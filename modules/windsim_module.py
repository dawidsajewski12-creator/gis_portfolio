"""
WindSim Module - Analiza Przepływu Wiatru CFD dla Suwałk
========================================================

Moduł implementujący uproszczone symulacje CFD (Computational Fluid Dynamics)
dla analizy przepływu wiatru w środowisku miejskim Suwałk.

Autor: Environmental Analytics Team
Wersja: 1.9.0
Data: Wrzesień 2025
"""

import numpy as np
from datetime import datetime
import json
from typing import Dict, List, Tuple, Optional
import math

class WindSimulator:
    """
    System analizy przepływu wiatru CFD dla Suwałk.
    
    Implementuje uproszczony model CFD z uwzględnieniem:
    - Profilu wiatru w warstwie przygranicznej atmosfery (ABL)
    - Efektów urbanistycznych (tunele wiatrowe, strefy cienia)
    - Komfortu pieszych według kryteriów Lawsona
    - Oddziaływania na konstrukcje budowlane
    
    Attributes:
        config (Dict): Konfiguracja projektu
        area_km2 (float): Powierzchnia obszaru analizy [km²]
        center_lat (float): Szerokość geograficzna centrum
        center_lng (float): Długość geograficzna centrum  
        building_density (float): Gęstość zabudowy [0-1]
        average_building_height (float): Średnia wysokość budynków [m]
        surface_roughness (float): Parametr szorstkości powierzchni [m]
    """
    
    def __init__(self, config: Dict):
        """
        Inicjalizuje symulator wiatru z parametrami dla Suwałk.
        
        Args:
            config (Dict): Konfiguracja projektu zawierająca lokalizację i parametry
        """
        self.config = config
        self.area_km2 = config['location']['area_km2']
        self.center_lat = config['location']['center_lat']
        self.center_lng = config['location']['center_lng']
        
        # Parametry urbanistyczne Suwałk (oparte na danych przestrzennych)
        self.building_density = 0.25        # 25% pokrycia budynkami w centrum
        self.average_building_height = 18   # m (2-4 kondygnacje dominant)
        self.surface_roughness = 0.3        # m (teren zurbanizowany wg WMO)
        
        # Parametry CFD
        self.air_density = 1.225            # kg/m³ (15°C, 1013 hPa)
        self.reference_height = 10.0        # m (standardowa wysokość pomiarowa)
        self.pedestrian_height = 1.5        # m (wysokość pieszego)
        self.von_karman_constant = 0.41     # stała von Karmana
        
        # Współczynniki empiryczne dla środowiska miejskiego
        self.tunnel_amplification = 0.8     # wzmocnienie w tunelach wiatrowych  
        self.wake_reduction = 0.3           # redukcja w strefach cienia
        self.green_area_reduction = 0.4     # redukcja przez zieleń
        
        print(f"💨 WindSim v1.9 initialized for {self.area_km2} km²")
        print(f"   🏗️ Zabudowa: {self.building_density*100:.0f}%, h_avg={self.average_building_height}m")
        print(f"   🌪️ Szorstkość: {self.surface_roughness}m (teren miejski)")
        print(f"   📐 Wysokość ref: {self.reference_height}m")
    
    def calculate_wind_profile(self, height: float, u_ref: float, 
                              z_ref: float = None, z0: float = None) -> float:
        """
        Oblicza prędkość wiatru na zadanej wysokości według profilu logarytmicznego ABL.
        
        Wykorzystuje model warstwy przygranicznej atmosfery (Atmospheric Boundary Layer)
        z uwzględnieniem szorstkości powierzchni miejskiej.
        
        Args:
            height (float): Wysokość nad gruntem [m]
            u_ref (float): Prędkość referencyjna [m/s]
            z_ref (float): Wysokość referencyjna [m] (domyślnie 10m)
            z0 (float): Parametr szorstkości [m] (domyślnie z konfiguracji)
            
        Returns:
            float: Prędkość wiatru na wysokości 'height' [m/s]
        """
        if z_ref is None:
            z_ref = self.reference_height
        if z0 is None:
            z0 = self.surface_roughness
            
        # Zabezpieczenie przed logarytmem z argumentu ≤ 0
        if height <= z0:
            height = z0 + 0.1
            
        # Profil logarytmiczny wiatru (ABL theory)
        wind_speed = u_ref * np.log((height + z0) / z0) / np.log((z_ref + z0) / z0)
        
        return max(0, wind_speed)
    
    def calculate_urban_effects(self, wind_speed_ref: float, direction: float) -> Dict[str, float]:
        """
        Oblicza efekty miejskie wpływające na przepływ wiatru.
        
        Args:
            wind_speed_ref (float): Referencyjna prędkość wiatru [m/s]
            direction (float): Kierunek wiatru [°]
            
        Returns:
            Dict[str, float]: Słownik z efektami miejskimi
        """
        # 1. Efekt tunelu wiatrowego między budynkami
        # Przyspieszenie wynikające z przewężenia przekroju
        tunnel_factor = 1.0 + (self.building_density * self.tunnel_amplification)
        max_tunnel_speed = wind_speed_ref * tunnel_factor
        
        # 2. Strefy cienia aerodynamicznego za budynkami
        # Redukcja prędkości w obszarach nawietrznych
        min_wake_speed = wind_speed_ref * (1 - self.wake_reduction)
        
        # 3. Efekt szorstkości miejskiej - redukcja średniej prędkości
        urban_reduction_factor = 1 - (self.building_density * 0.4)
        avg_urban_speed = wind_speed_ref * urban_reduction_factor
        
        # 4. Prędkość na poziomie pieszego (1.5m)
        pedestrian_speed = self.calculate_wind_profile(
            self.pedestrian_height, wind_speed_ref
        )
        
        # 5. Efekty kierunkowe (anizotropia ze względu na układ ulic)
        directional_factor = self._calculate_directional_factor(direction)
        
        return {
            'max_tunnel_speed': max_tunnel_speed * directional_factor,
            'min_wake_speed': min_wake_speed * directional_factor,
            'avg_urban_speed': avg_urban_speed * directional_factor,
            'pedestrian_speed': pedestrian_speed * directional_factor,
            'directional_factor': directional_factor,
            'tunnel_factor': tunnel_factor,
            'wake_reduction_pct': self.wake_reduction * 100
        }
    
    def _calculate_directional_factor(self, direction: float) -> float:
        """
        Oblicza współczynnik kierunkowy uwzględniający układ ulic w Suwałkach.
        
        Args:
            direction (float): Kierunek wiatru [°]
            
        Returns:
            float: Współczynnik kierunkowy [0.8-1.2]
        """
        # Główne kierunki ulic w Suwałkach (N-S, E-W orientation)
        main_street_directions = [0, 90, 180, 270]  # N, E, S, W
        
        # Znajdź najbliższy główny kierunek
        min_angle_diff = min(abs(direction - street_dir) for street_dir in main_street_directions)
        
        # Im bliżej głównego kierunku, tym większe wzmocnienie (tunele wiatrowe)
        if min_angle_diff <= 15:      # ±15° od głównego kierunku
            return 1.15               # +15% wzmocnienie
        elif min_angle_diff <= 30:    # ±30° 
            return 1.05               # +5% wzmocnienie
        else:                         # Kierunki poprzeczne
            return 0.9                # -10% redukcja
    
    def assess_pedestrian_comfort(self, wind_speed: float) -> Tuple[str, int, str]:
        """
        Ocenia komfort pieszych według kryteriów Lawsona.
        
        Kryteria Lawsona (British standard for wind comfort):
        - < 4 m/s: Komfortowo (siedzenie, spacer)
        - 4-6 m/s: Akceptowalne (krótkie przebywanie)  
        - 6-8 m/s: Niewłaściwe (tylko przejście)
        - > 8 m/s: Niebezpieczne (utrudnione chodzenie)
        
        Args:
            wind_speed (float): Prędkość wiatru [m/s]
            
        Returns:
            Tuple[str, int, str]: (poziom_komfortu, score, opis)
        """
        if wind_speed < 4:
            return "KOMFORTOWO", 1, "Warunki idealne do przebywania na zewnątrz"
        elif wind_speed < 6:
            return "AKCEPTOWALNE", 2, "Odpowiednie do spacerów i krótkiego przebywania"
        elif wind_speed < 8:
            return "NIEWŁAŚCIWE", 3, "Tylko do szybkiego przejścia, dyskomfort"
        elif wind_speed < 12:
            return "NIEBEZPIECZNE", 4, "Trudności w chodzeniu, ryzyko upadku"
        else:
            return "EKSTREMALNIE NIEBEZPIECZNE", 5, "Niemożliwe przebywanie na zewnątrz"
    
    def calculate_wind_pressure(self, wind_speed: float) -> Dict[str, float]:
        """
        Oblicza ciśnienia wiatru na konstrukcje budowlane.
        
        Args:
            wind_speed (float): Prędkość wiatru [m/s]
            
        Returns:
            Dict[str, float]: Ciśnienia w różnych strefach [Pa]
        """
        # Ciśnienie dynamiczne wiatru (q = 0.5 * ρ * v²)
        dynamic_pressure = 0.5 * self.air_density * wind_speed**2
        
        # Współczynniki ciśnienia dla typowej geometrii miejskiej
        cp_windward = 0.8      # strona nawietrzna (+)
        cp_leeward = -0.5      # strona zawietrzna (-)
        cp_side = -0.7         # ściany boczne (-)
        cp_roof_windward = -0.3 # dach nawietrzny (-)
        cp_roof_leeward = -0.6  # dach zawietrzny (-)
        
        return {
            'dynamic_pressure_pa': dynamic_pressure,
            'windward_pressure_pa': dynamic_pressure * cp_windward,
            'leeward_pressure_pa': dynamic_pressure * cp_leeward,
            'side_pressure_pa': dynamic_pressure * cp_side,
            'roof_windward_pa': dynamic_pressure * cp_roof_windward,
            'roof_leeward_pa': dynamic_pressure * cp_roof_leeward,
            'pressure_difference_pa': dynamic_pressure * (cp_windward - cp_leeward)
        }
    
    def generate_wind_field(self, scenario_name: str, wind_speed_ref: float, 
                           direction: float, urban_effects: Dict) -> List[Dict]:
        """
        Generuje pole wiatru do wizualizacji na mapie.
        
        Args:
            scenario_name (str): Nazwa scenariusza
            wind_speed_ref (float): Referencyjna prędkość wiatru [m/s]
            direction (float): Kierunek wiatru [°]
            urban_effects (Dict): Efekty miejskie
            
        Returns:
            List[Dict]: Lista punktów pola wiatru z wektorami prędkości
        """
        # Deterministyczne generowanie punktów (powtarzalne wyniki)
        seed_value = abs(int(direction) + int(wind_speed_ref * 10)) % (2**31)
        np.random.seed(seed_value)
        
        # Liczba punktów proporcjonalna do prędkości wiatru
        num_points = min(100, max(20, int(wind_speed_ref * 5)))
        
        wind_field_points = []
        
        for i in range(num_points):
            # Lokalizacja punktu (rozkład normalny wokół centrum)
            lat = self.center_lat + np.random.normal(0, 0.008)   # ~±900m
            lng = self.center_lng + np.random.normal(0, 0.012)   # ~±1200m
            
            # Lokalna prędkość z wariancją przestrzenną  
            spatial_variation = np.random.uniform(0.6, 1.4)
            
            # Wybór typu mikrośrodowiska
            environment_type = np.random.choice(
                ['open', 'tunnel', 'wake', 'green', 'intersection'],
                p=[0.3, 0.2, 0.2, 0.15, 0.15]
            )
            
            # Modyfikacja prędkości według mikrośrodowiska
            if environment_type == 'tunnel':
                local_speed = urban_effects['max_tunnel_speed'] * spatial_variation
                turbulence = 0.25  # Wysoka turbulencja w tunelach
            elif environment_type == 'wake':
                local_speed = urban_effects['min_wake_speed'] * spatial_variation  
                turbulence = 0.15  # Średnia turbulencja w strefach cienia
            elif environment_type == 'green':
                local_speed = urban_effects['avg_urban_speed'] * (1 - self.green_area_reduction) * spatial_variation
                turbulence = 0.1   # Niska turbulencja w parkach
            elif environment_type == 'intersection':
                local_speed = urban_effects['avg_urban_speed'] * 1.1 * spatial_variation  # Lekkie wzmocnienie
                turbulence = 0.2   # Podwyższona turbulencja na skrzyżowaniach
            else:  # 'open'
                local_speed = urban_effects['avg_urban_speed'] * spatial_variation
                turbulence = 0.12  # Średnia turbulencja terenu otwartego
            
            # Lokalny kierunek wiatru z odchyleniami od głównego
            direction_deviation = np.random.normal(0, 25)  # ±25° standardowo
            if environment_type in ['tunnel', 'intersection']:
                direction_deviation *= 1.5  # Większe odchylenia w złożonych strukturach
            
            local_direction = (direction + direction_deviation) % 360
            
            # Składowe wektora wiatru (konwencja meteorologiczna -> matematyczna)
            wind_angle_rad = np.radians(270 - local_direction)  # Konwersja: N=90°→0°, E=0°→270°
            vx = local_speed * np.cos(wind_angle_rad)           # Składowa E-W
            vy = local_speed * np.sin(wind_angle_rad)           # Składowa N-S
            
            # Wysokość nad gruntem dla tego punktu
            height_agl = np.random.uniform(1.0, 20.0)  # 1-20m nad gruntem
            
            wind_field_points.append({
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "speed": round(local_speed, 2),
                "direction": round(local_direction, 1),
                "vx": round(vx, 2),
                "vy": round(vy, 2),
                "height_agl": round(height_agl, 1),
                "turbulence_intensity": round(turbulence, 3),
                "environment_type": environment_type,
                "gust_factor": round(1 + turbulence * 0.5, 2)  # Współczynnik porywów
            })
        
        return wind_field_points
    
    def calculate_comfort_zones_distribution(self, urban_effects: Dict) -> Dict[str, float]:
        """
        Oblicza rozkład stref komfortu w obszarze miejskim.
        
        Args:
            urban_effects (Dict): Efekty miejskie na przepływ wiatru
            
        Returns:
            Dict[str, float]: Procentowy rozkład stref komfortu
        """
        avg_speed = urban_effects['avg_urban_speed']
        
        # Model empiryczny rozkładu komfortu w zależności od średniej prędkości
        if avg_speed < 3:
            comfort_zones = {"komfortowo": 90, "akceptowalne": 8, "niewłaściwe": 2, "niebezpieczne": 0}
        elif avg_speed < 5:
            comfort_zones = {"komfortowo": 70, "akceptowalne": 20, "niewłaściwe": 8, "niebezpieczne": 2}
        elif avg_speed < 8:
            comfort_zones = {"komfortowo": 40, "akceptowalne": 35, "niewłaściwe": 20, "niebezpieczne": 5}
        elif avg_speed < 12:
            comfort_zones = {"komfortowo": 15, "akceptowalne": 25, "niewłaściwe": 40, "niebezpieczne": 20}
        else:
            comfort_zones = {"komfortowo": 5, "akceptowalne": 10, "niewłaściwe": 30, "niebezpieczne": 55}
        
        return comfort_zones
    
    def simulate_scenario(self, wind_speed_ref: float, direction: float, 
                         scenario_name: str, detailed_output: bool = True) -> Dict:
        """
        Główna funkcja symulująca scenariusz wiatru.
        
        Args:
            wind_speed_ref (float): Referencyjna prędkość wiatru [m/s]
            direction (float): Kierunek wiatru [° from North]
            scenario_name (str): Nazwa scenariusza
            detailed_output (bool): Czy generować szczegółowe dane wyjściowe
            
        Returns:
            Dict: Kompletne wyniki symulacji CFD
        """
        print(f"\n💨 WindSim: {scenario_name}")
        print(f"   🧭 Wiatr: {wind_speed_ref} m/s z kierunku {direction}°")
        
        # Oblicz efekty miejskie
        urban_effects = self.calculate_urban_effects(wind_speed_ref, direction)
        
        # Oceń komfort pieszych
        pedestrian_comfort, comfort_score, comfort_description = \
            self.assess_pedestrian_comfort(urban_effects['pedestrian_speed'])
        
        # Oblicz ciśnienia wiatru
        wind_pressures = self.calculate_wind_pressure(wind_speed_ref)
        
        # Rozkład stref komfortu
        comfort_zones = self.calculate_comfort_zones_distribution(urban_effects)
        comfort_zones_percent = comfort_zones['komfortowo'] + comfort_zones['akceptowalne']
        
        # Generuj pole wiatru do wizualizacji
        wind_field = []
        if detailed_output:
            wind_field = self.generate_wind_field(scenario_name, wind_speed_ref, direction, urban_effects)
        
        # Strukturyzacja wyników
        result = {
            'scenario_name': scenario_name,
            'module': 'WindSim',
            'model_version': 'WindSim_v1.9_CFD',
            'computation_time': datetime.now().isoformat(),
            
            'parameters': {
                'wind_speed_ref': wind_speed_ref,
                'wind_direction': direction,
                'reference_height': self.reference_height,
                'surface_roughness': self.surface_roughness,
                'air_density': self.air_density
            },
            
            'urban_characteristics': {
                'building_density_percent': self.building_density * 100,
                'average_building_height': self.average_building_height,
                'tunnel_amplification': self.tunnel_amplification,
                'wake_reduction': self.wake_reduction,
                'directional_factor': urban_effects['directional_factor']
            },
            
            'wind_field_analysis': {
                'max_speed': round(urban_effects['max_tunnel_speed'], 2),
                'min_speed': round(urban_effects['min_wake_speed'], 2), 
                'avg_urban_speed': round(urban_effects['avg_urban_speed'], 2),
                'pedestrian_speed': round(urban_effects['pedestrian_speed'], 2),
                'speed_variation_factor': round(urban_effects['max_tunnel_speed'] / urban_effects['min_wake_speed'], 2)
            },
            
            'comfort_assessment': {
                'pedestrian_comfort_level': pedestrian_comfort,
                'comfort_score': comfort_score,
                'comfort_description': comfort_description,
                'comfort_zones_percent': round(comfort_zones_percent, 1),
                'comfort_distribution': comfort_zones
            },
            
            'structural_loads': {
                'dynamic_pressure_pa': round(wind_pressures['dynamic_pressure_pa'], 0),
                'windward_pressure_pa': round(wind_pressures['windward_pressure_pa'], 0),
                'leeward_pressure_pa': round(wind_pressures['leeward_pressure_pa'], 0),
                'pressure_difference_pa': round(wind_pressures['pressure_difference_pa'], 0),
                'design_wind_load_knm2': round(wind_pressures['dynamic_pressure_pa'] / 1000, 2)
            }
        }
        
        # Dodaj pole wiatru jeśli wymagane  
        if detailed_output:
            result['wind_field'] = wind_field
            result['visualization'] = {
                'center_lat': self.center_lat,
                'center_lng': self.center_lng, 
                'zoom_level': 14,
                'vector_scale': 10,
                'color_scale': 'Viridis',
                'particle_count': len(wind_field)
            }
        
        # Logi wynikowe
        print(f"   📊 Prędkość: {urban_effects['min_wake_speed']:.1f}-{urban_effects['max_tunnel_speed']:.1f} m/s")
        print(f"   👥 Komfort pieszych: {comfort_zones_percent:.0f}% obszaru ({pedestrian_comfort})")
        print(f"   🏗️ Ciśnienie na budynki: {wind_pressures['dynamic_pressure_pa']:.0f} Pa")
        print(f"   🌪️ Intensywność turbulencji: {comfort_score}/5")
        
        return result
    
    def batch_simulate(self, scenarios: List[Tuple[float, float, str]]) -> Dict[str, Dict]:
        """
        Uruchamia batch symulacji CFD dla wielu scenariuszy.
        
        Args:
            scenarios (List[Tuple]): Lista (wind_speed, direction, name)
            
        Returns:
            Dict[str, Dict]: Wyniki wszystkich scenariuszy  
        """
        results = {}
        
        print(f"\n🔄 CFD Batch simulation: {len(scenarios)} scenarios")
        
        for i, (speed, direction, name) in enumerate(scenarios, 1):
            print(f"\n[{i}/{len(scenarios)}]", end=" ")
            result = self.simulate_scenario(speed, direction, name)
            key = name.lower().replace(" ", "_").replace("-", "")
            results[key] = result
        
        print(f"\n✅ CFD Batch completed: {len(results)} scenarios")
        return results
    
    def export_results(self, results: Dict, output_file: str = "wind_results.json"):
        """
        Eksportuje wyniki CFD do pliku JSON.
        
        Args:
            results (Dict): Wyniki symulacji
            output_file (str): Nazwa pliku wyjściowego
        """
        export_data = {
            "metadata": {
                "module": "WindSim",
                "version": "1.9.0",
                "cfd_model": "Simplified Urban CFD with ABL",
                "location": self.config['location'],
                "generated": datetime.now().isoformat(),
                "scenarios_count": len(results)
            },
            "configuration": {
                "building_density": self.building_density,
                "average_building_height": self.average_building_height,
                "surface_roughness": self.surface_roughness,
                "reference_height": self.reference_height,
                "comfort_criteria": "Lawson (British Standard)"
            },
            "results": results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"💾 CFD results exported to: {output_file}")

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
    
    # Inicjalizacja symulatora CFD
    wind_sim = WindSimulator(test_config)
    
    # Pojedyncza symulacja
    result = wind_sim.simulate_scenario(15, 270, "Test silny wiatr zachodni")
    
    # Batch symulacja
    scenarios = [
        (5, 270, "Wiatr spokojny - zachód"),
        (15, 315, "Wiatr silny - NW"),
        (25, 270, "Wiatr burzowy - zachód")
    ]
    
    batch_results = wind_sim.batch_simulate(scenarios)
    wind_sim.export_results(batch_results, "wind_batch_results.json")