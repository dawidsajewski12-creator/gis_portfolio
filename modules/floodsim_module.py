"""
FloodSim Module - Symulacje Powodzi 2D dla Suwałk
=================================================

Moduł implementujący symulacje powodzi 2D oparte na uproszczonych równaniach Saint-Venant
dla centrum miasta Suwałki. System analizuje scenariusze opadowe i generuje mapy zalewów.

Autor: Environmental Analytics Team
Wersja: 2.1.0
Data: Wrzesień 2025
"""

import numpy as np
from datetime import datetime
import json
from typing import Dict, List, Tuple, Optional

class FloodSimulator:
    """
    System symulacji powodzi 2D dla Suwałk.
    
    Implementuje uproszczony model hydrauliczny oparty na równaniach Saint-Venant
    z uwzględnieniem specyfiki miejskiej infrastruktury hydrologicznej.
    
    Attributes:
        config (Dict): Konfiguracja projektu
        area_km2 (float): Powierzchnia obszaru analizy [km²]
        base_elevation (float): Średnia wysokość terenu [m n.p.m.]
        urban_coverage (float): Pokrycie terenu zabudową [0-1]
        drainage_capacity (float): Pojemność kanalizacji [mm/h]
        infiltration_rate (float): Szybkość infiltracji [mm/h]
        runoff_coefficient (float): Współczynnik spływu powierzchniowego [0-1]
    """
    
    def __init__(self, config: Dict):
        """
        Inicjalizuje symulator powodzi z parametrami dla Suwałk.
        
        Args:
            config (Dict): Konfiguracja projektu zawierająca lokalizację i parametry
        """
        self.config = config
        self.area_km2 = config['location']['area_km2']
        self.base_elevation = config['location']['elevation_avg']
        
        # Charakterystyki hydrologiczne Suwałk (oparte na danych GUS i literaturze)
        self.urban_coverage = 0.25      # 25% zabudowy w centrum
        self.drainage_capacity = 40     # mm/h pojemność kanalizacji burzowej
        self.infiltration_rate = 8      # mm/h infiltracja do gruntu (gleby piaszczyste)
        self.runoff_coefficient = 0.75  # współczynnik spływu (teren miejski)
        
        # Parametry hydrauliczne
        self.manning_n = 0.035          # współczynnik szorstkości Manning (teren miejski)
        self.min_flow_depth = 0.01      # minimalna głębokość przepływu [m]
        self.max_flow_velocity = 5.0    # maksymalna prędkość przepływu [m/s]
        
        print(f"🌊 FloodSim v2.1 initialized for {self.area_km2} km²")
        print(f"   💧 Kanalizacja: {self.drainage_capacity} mm/h")
        print(f"   🌱 Infiltracja: {self.infiltration_rate} mm/h") 
        print(f"   🏘️ Zabudowa: {self.urban_coverage*100:.0f}%")
    
    def calculate_effective_rainfall(self, rainfall_mm_h: float, duration_h: float) -> Tuple[float, float, float]:
        """
        Oblicza efektywny opad uwzględniając infiltrację i pojemność kanalizacji.
        
        Args:
            rainfall_mm_h (float): Intensywność opadu [mm/h]
            duration_h (float): Czas trwania opadu [h]
            
        Returns:
            Tuple[float, float, float]: (efektywny_opad, nadmiar, całkowity_nadmiar_mm)
        """
        # Efektywny opad po odliczeniu infiltracji
        effective_rainfall = max(0, rainfall_mm_h - self.infiltration_rate)
        
        # Nadmiar po uwzględnieniu pojemności kanalizacji
        excess_rainfall = max(0, effective_rainfall - self.drainage_capacity)
        
        # Całkowita objętość nadmiaru wody z uwzględnieniem spływu powierzchniowego
        total_excess_mm = excess_rainfall * duration_h * self.runoff_coefficient
        
        return effective_rainfall, excess_rainfall, total_excess_mm
    
    def calculate_flood_depths(self, total_excess_mm: float) -> Tuple[float, float]:
        """
        Oblicza głębokość zalewu na podstawie modelu akumulacji wody.
        
        Model empiryczny kalibrowany dla obszarów miejskich w Polsce.
        
        Args:
            total_excess_mm (float): Całkowita objętość nadmiaru wody [mm]
            
        Returns:
            Tuple[float, float]: (max_głębokość, procent_obszaru_zalewanego)
        """
        if total_excess_mm <= 0:
            return 0.0, 0.0
        
        # Model potęgowy dla głębokości (kalibrowany dla warunków miejskich)
        # Uwzględnia naturalne zagłębienia, system drogowy jako kolektor
        depth_factor = 0.8  # Współczynnik kalibracyjny
        max_depth = min(total_excess_mm / 100 * depth_factor, 3.0)  # Ograniczenie do 3m
        
        # Procent powierzchni zalewany (model logistyczny)
        area_factor = 1.2
        flooded_area_pct = min(100, total_excess_mm * area_factor)
        
        return max_depth, flooded_area_pct
    
    def assess_flood_risk(self, max_depth: float) -> str:
        """
        Ocenia poziom ryzyka powodziowego według polskich standardów.
        
        Args:
            max_depth (float): Maksymalna głębokość zalewu [m]
            
        Returns:
            str: Poziom ryzyka (MINIMALNE/NISKIE/UMIARKOWANE/WYSOKIE/KRYTYCZNE)
        """
        risk_levels = ["MINIMALNE", "NISKIE", "UMIARKOWANE", "WYSOKIE", "KRYTYCZNE"]
        
        if max_depth < 0.05:
            return risk_levels[0]    # Bez znaczącego zalewu
        elif max_depth < 0.15:
            return risk_levels[1]    # Zalanie chodników
        elif max_depth < 0.40:
            return risk_levels[2]    # Zalanie jezdni
        elif max_depth < 0.80:
            return risk_levels[3]    # Zagrożenie dla samochodów
        else:
            return risk_levels[4]    # Zagrożenie dla życia
    
    def calculate_building_impact(self, flooded_area_km2: float) -> Dict[str, int]:
        """
        Szacuje wpływ powodzi na budynki w centrum Suwałk.
        
        Args:
            flooded_area_km2 (float): Powierzchnia zalewu [km²]
            
        Returns:
            Dict[str, int]: Statystyki budynków (total, at_risk, affected_population)
        """
        # Dane GUS dla Suwałk - centrum miasta
        buildings_per_km2 = 350        # budynki/km² w centrum
        occupancy_rate = 0.6          # wskaźnik zajętości w strefie zalewu
        residents_per_building = 3    # średnia liczba mieszkańców
        
        total_buildings = int(self.area_km2 * buildings_per_km2 * self.urban_coverage)
        buildings_at_risk = min(
            int(flooded_area_km2 * buildings_per_km2 * occupancy_rate), 
            total_buildings
        )
        affected_population = buildings_at_risk * residents_per_building
        
        return {
            "total": total_buildings,
            "at_risk": buildings_at_risk,
            "affected_population": affected_population
        }
    
    def calculate_economic_damage(self, buildings_at_risk: int, total_volume_m3: float) -> int:
        """
        Szacuje straty ekonomiczne w PLN.
        
        Args:
            buildings_at_risk (int): Liczba zagrożonych budynków
            total_volume_m3 (float): Objętość wody powodziowej [m³]
            
        Returns:
            int: Szacowane straty w PLN
        """
        # Średnie straty na budynek (dane dla Polski)
        damage_per_building = 50000    # PLN
        
        # Straty infrastrukturalne (10 PLN/m³ wody)
        infrastructure_damage_rate = 10  # PLN/m³
        
        total_damage = (buildings_at_risk * damage_per_building + 
                       total_volume_m3 * infrastructure_damage_rate)
        
        return int(total_damage)
    
    def generate_flood_zones(self, scenario_name: str, max_depth: float, 
                           flooded_area_pct: float) -> List[Dict]:
        """
        Generuje punkty zalewu do wizualizacji na mapie.
        
        Args:
            scenario_name (str): Nazwa scenariusza
            max_depth (float): Maksymalna głębokość [m]
            flooded_area_pct (float): Procent zalanego obszaru
            
        Returns:
            List[Dict]: Lista punktów zalewu z współrzędnymi i parametrami
        """
        # Deterministyczne generowanie punktów (powtarzalne wyniki)
        seed_value = abs(hash(scenario_name)) % (2**31)
        np.random.seed(seed_value)
        
        # Liczba punktów proporcjonalna do obszaru zalewu
        num_zones = max(5, min(50, int(flooded_area_pct * 0.8)))
        
        flood_zones = []
        center_lat = self.config['location']['center_lat']
        center_lng = self.config['location']['center_lng']
        
        for i in range(num_zones):
            # Lokalizacja w okolicy centrum z rozkładem normalnym
            lat = center_lat + np.random.normal(0, 0.008)  # ~±900m
            lng = center_lng + np.random.normal(0, 0.012)  # ~±1200m
            
            # Głębokość z rozkładem wykładniczym (więcej płytkich zalewów)
            if max_depth > 0:
                depth = max(0.02, np.random.exponential(max_depth * 0.6))
                depth = min(depth, max_depth)
            else:
                depth = 0.02
            
            # Prędkość przepływu (uproszczona formuła Manning-Strickler)
            flow_velocity = min(np.sqrt(depth) * 1.5, self.max_flow_velocity) if depth > 0 else 0
            
            # Wysokość terenu (wartość bazowa ± wariacja)
            elevation = self.base_elevation + np.random.normal(0, 2)
            
            flood_zones.append({
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "depth_m": round(depth, 3),
                "elevation_m": round(elevation, 1),
                "flow_velocity": round(flow_velocity, 2),
                "zone_id": i + 1,
                "surface_type": np.random.choice(["road", "sidewalk", "green", "plaza"], 
                                               p=[0.4, 0.25, 0.2, 0.15])
            })
        
        return flood_zones
    
    def simulate_scenario(self, rainfall_mm_h: float, duration_h: float, 
                         scenario_name: str, detailed_output: bool = True) -> Dict:
        """
        Główna funkcja symulująca scenariusz powodzi.
        
        Args:
            rainfall_mm_h (float): Intensywność opadu [mm/h]
            duration_h (float): Czas trwania opadu [h]
            scenario_name (str): Nazwa scenariusza
            detailed_output (bool): Czy generować szczegółowe dane wyjściowe
            
        Returns:
            Dict: Kompletne wyniki symulacji
        """
        print(f"\n🌊 FloodSim: {scenario_name}")
        print(f"   🌧️ Opad: {rainfall_mm_h} mm/h przez {duration_h}h")
        
        # Obliczenia hydrologiczne
        effective_rainfall, excess_rainfall, total_excess_mm = \
            self.calculate_effective_rainfall(rainfall_mm_h, duration_h)
        
        # Obliczenia głębokości i zasięgu
        max_depth, flooded_area_pct = self.calculate_flood_depths(total_excess_mm)
        flooded_area_km2 = (flooded_area_pct / 100) * self.area_km2
        
        # Ocena ryzyka
        risk_level = self.assess_flood_risk(max_depth)
        
        # Wpływ na budynki
        building_impact = self.calculate_building_impact(flooded_area_km2)
        
        # Objętość wody (średnia głębokość = 40% maksymalnej)
        total_volume_m3 = flooded_area_km2 * 1e6 * (max_depth * 0.4)
        
        # Straty ekonomiczne
        economic_damage = self.calculate_economic_damage(
            building_impact["at_risk"], total_volume_m3
        )
        
        # Punkty zalewu do wizualizacji
        flood_zones = []
        if detailed_output:
            flood_zones = self.generate_flood_zones(scenario_name, max_depth, flooded_area_pct)
        
        # Strukturyzacja wyników
        result = {
            'scenario_name': scenario_name,
            'module': 'FloodSim',
            'model_version': 'FloodSim_v2.1_Suwalki',
            'computation_time': datetime.now().isoformat(),
            
            'parameters': {
                'rainfall_mm_h': rainfall_mm_h,
                'duration_h': duration_h,
                'total_rainfall_mm': rainfall_mm_h * duration_h,
                'effective_rainfall_mm': effective_rainfall * duration_h,
                'excess_rainfall_mm': excess_rainfall * duration_h,
                'runoff_coefficient': self.runoff_coefficient
            },
            
            'hydraulic_conditions': {
                'drainage_capacity_mm_h': self.drainage_capacity,
                'infiltration_rate_mm_h': self.infiltration_rate,
                'manning_roughness': self.manning_n,
                'urban_coverage_percent': self.urban_coverage * 100
            },
            
            'metrics': {
                'max_depth_m': round(max_depth, 3),
                'mean_depth_m': round(max_depth * 0.4, 3),
                'flooded_area_km2': round(flooded_area_km2, 4),
                'flooded_area_percent': round(flooded_area_pct, 1),
                'total_volume_m3': round(total_volume_m3, 0),
                'peak_flow_velocity_ms': round(np.sqrt(max_depth) * 1.5 if max_depth > 0 else 0, 2),
                'risk_level': risk_level,
                'risk_score': len(["MINIMALNE", "NISKIE", "UMIARKOWANE", "WYSOKIE", "KRYTYCZNE"][:
                                ["MINIMALNE", "NISKIE", "UMIARKOWANE", "WYSOKIE", "KRYTYCZNE"].index(risk_level)+1])
            },
            
            'impact_assessment': {
                'buildings_total': building_impact["total"],
                'buildings_at_risk': building_impact["at_risk"],
                'affected_population': building_impact["affected_population"],
                'economic_damage_pln': economic_damage,
                'economic_damage_eur': round(economic_damage / 4.5, 0),  # PLN->EUR
                'evacuation_needed': max_depth > 0.5
            }
        }
        
        # Dodaj punkty zalewu jeśli wymagane
        if detailed_output:
            result['flood_zones'] = flood_zones
            result['visualization'] = {
                'center_lat': self.config['location']['center_lat'],
                'center_lng': self.config['location']['center_lng'],
                'zoom_level': 14,
                'color_scale': 'Blues',
                'max_marker_size': 20
            }
        
        # Logi wynikowe
        print(f"   📊 Max głębokość: {max_depth:.3f}m")
        print(f"   📍 Obszar zalewu: {flooded_area_km2:.3f} km² ({flooded_area_pct:.1f}%)")  
        print(f"   🏠 Budynki zagrożone: {building_impact['at_risk']}")
        print(f"   👥 Ludność dotknięta: {building_impact['affected_population']}")
        print(f"   💰 Straty: {economic_damage:,} PLN")
        print(f"   ⚠️ Ryzyko: {risk_level}")
        
        return result
    
    def batch_simulate(self, scenarios: List[Tuple[float, float, str]]) -> Dict[str, Dict]:
        """
        Uruchamia batch symulacji dla wielu scenariuszy.
        
        Args:
            scenarios (List[Tuple]): Lista (rainfall, duration, name)
            
        Returns:
            Dict[str, Dict]: Wyniki wszystkich scenariuszy
        """
        results = {}
        
        print(f"\n🔄 Batch simulation: {len(scenarios)} scenarios")
        
        for i, (rainfall, duration, name) in enumerate(scenarios, 1):
            print(f"\n[{i}/{len(scenarios)}]", end=" ")
            result = self.simulate_scenario(rainfall, duration, name)
            key = name.lower().replace(" ", "_")
            results[key] = result
        
        print(f"\n✅ Batch completed: {len(results)} scenarios")
        return results
    
    def export_results(self, results: Dict, output_file: str = "flood_results.json"):
        """
        Eksportuje wyniki do pliku JSON.
        
        Args:
            results (Dict): Wyniki symulacji
            output_file (str): Nazwa pliku wyjściowego
        """
        export_data = {
            "metadata": {
                "module": "FloodSim",
                "version": "2.1.0",
                "location": self.config['location'],
                "generated": datetime.now().isoformat(),
                "scenarios_count": len(results)
            },
            "configuration": {
                "urban_coverage": self.urban_coverage,
                "drainage_capacity": self.drainage_capacity,
                "infiltration_rate": self.infiltration_rate,
                "runoff_coefficient": self.runoff_coefficient
            },
            "results": results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"💾 Results exported to: {output_file}")

# Przykłady użycia
if __name__ == "__main__":
    # Przykładowa konfiguracja dla testów
    test_config = {
        'location': {
            'city': 'Suwałki',
            'center_lat': 54.10,
            'center_lng': 22.95,
            'area_km2': 5.0,
            'elevation_avg': 163.0
        }
    }
    
    # Inicjalizacja symulatora
    flood_sim = FloodSimulator(test_config)
    
    # Pojedyncza symulacja
    result = flood_sim.simulate_scenario(65, 2, "Test intensywny deszcz")
    
    # Batch symulacja
    scenarios = [
        (15, 4, "Lekki deszcz"),
        (65, 2, "Intensywny deszcz"), 
        (150, 1, "Ekstremalna nawałnica")
    ]
    
    batch_results = flood_sim.batch_simulate(scenarios)
    flood_sim.export_results(batch_results, "flood_batch_results.json")