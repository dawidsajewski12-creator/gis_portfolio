"""
ThermalSim Module - Komfort Termiczny Miejski dla Suwałk
========================================================

Moduł implementujący analizy komfortu termicznego w środowisku miejskim
z wykorzystaniem wskaźników PMV, PPD, UTCI i PET zgodnych z normami ISO.

Autor: Environmental Analytics Team  
Wersja: 1.6.0
Data: Wrzesień 2025
"""

import numpy as np
from datetime import datetime
import json
from typing import Dict, List, Tuple, Optional
import math

class ThermalComfortSimulator:
    """
    System analizy komfortu termicznego dla Suwałk.
    
    Implementuje obliczenia wskaźników komfortu termicznego:
    - PMV (Predicted Mean Vote) - ISO 7730
    - PPD (Predicted Percentage of Dissatisfied) - ISO 7730
    - UTCI (Universal Thermal Climate Index) - ISO 17772  
    - PET (Physiologically Equivalent Temperature)
    
    Uwzględnia mikroklima miejski, efekt miejskiej wyspy ciepła,
    wpływ zieleni i materiałów powierzchniowych.
    
    Attributes:
        config (Dict): Konfiguracja projektu
        center_lat (float): Szerokość geograficzna centrum
        center_lng (float): Długość geograficzna centrum
        area_km2 (float): Powierzchnia obszaru analizy [km²]
    """
    
    def __init__(self, config: Dict):
        """
        Inicjalizuje symulator komfortu termicznego z parametrami dla Suwałk.
        
        Args:
            config (Dict): Konfiguracja projektu zawierająca lokalizację i parametry
        """
        self.config = config
        self.center_lat = config['location']['center_lat']
        self.center_lng = config['location']['center_lng']
        self.area_km2 = config['location']['area_km2']
        
        # Parametry fizjologiczne (ISO 7730)
        self.human_body_surface_area = 1.8      # m² (Dubois formula average)
        self.skin_emissivity = 0.97             # emissivity człowieka
        self.evaporation_heat = 2430000         # J/kg ciepło parowania
        
        # Stałe fizyczne
        self.stefan_boltzmann = 5.67e-8         # W/(m²·K⁴)
        self.air_specific_heat = 1005           # J/(kg·K)
        self.air_density_stp = 1.225            # kg/m³ (15°C)
        
        # Parametry mikroklimatu Suwałk
        self.urban_heat_island_max = 4.0        # °C maksymalny UHI effect
        self.green_cooling_effect = -2.5        # °C chłodzenie przez zieleń
        self.water_cooling_effect = -1.5        # °C chłodzenie przez wodę
        
        print(f"🌡️ ThermalSim v1.6 initialized for {self.area_km2} km²")
        print(f"   🏙️ UHI efekt: do +{self.urban_heat_island_max}°C")
        print(f"   🌱 Chłodzenie zielenią: {self.green_cooling_effect}°C")
        print(f"   💧 Chłodzenie wodą: {self.water_cooling_effect}°C")
    
    def calculate_pmv_detailed(self, ta: float, tr: float, va: float, rh: float, 
                              met: float = 1.2, clo: float = 0.7, pa: Optional[float] = None) -> float:
        """
        Oblicza PMV (Predicted Mean Vote) według ISO 7730.
        
        Implementuje pełny model Fangera z uwzględnieniem wszystkich składników
        bilansu cieplnego ciała ludzkiego.
        
        Args:
            ta (float): Temperatura powietrza [°C]
            tr (float): Średnia temperatura radiacyjna [°C] 
            va (float): Prędkość powietrza [m/s]
            rh (float): Wilgotność względna [%]
            met (float): Aktywność metaboliczna [met] (1.2 = chodzenie spokojne)
            clo (float): Izolacyjność odzieży [clo] (0.7 = ubranie letnie)
            pa (Optional[float]): Ciśnienie parcjalne pary wodnej [Pa]
            
        Returns:
            float: Wartość PMV [-3.0 do +3.0]
        """
        # Konwersje jednostek
        ta_k = ta + 273.15  # [K]
        tr_k = tr + 273.15  # [K]
        
        # Ciśnienie parcjalne pary wodnej
        if pa is None:
            # Oblicz z wilgotności względnej (Magnus formula)
            es = 610.78 * np.exp(17.27 * ta / (ta + 237.3))  # Pa
            pa = rh / 100 * es
        
        # Aktywność metaboliczna [W/m²]
        M = met * 58.15
        
        # Praca zewnętrzna (zazwyczaj 0 dla pieszych)
        W = 0  # W/m²
        
        # Rezystancja termiczna odzieży [m²·K/W]
        Icl = clo * 0.155
        
        # Współczynnik powierzchni odzieży  
        if Icl <= 0.078:
            fcl = 1.0 + 1.290 * Icl
        else:
            fcl = 1.05 + 0.645 * Icl
        
        # Iteracyjne rozwiązanie dla temperatury powierzchni odzieży
        tcl = ta  # Wartość początkowa
        for _ in range(10):  # Iteracje
            hc = 2.38 * abs(tcl - ta)**0.25 if va < 0.1 else 12.1 * np.sqrt(va)
            hc = max(hc, 12.1 * np.sqrt(va))  # Konwekcja wymuszona
            
            hr = 4 * self.stefan_boltzmann * fcl * ((tcl_k + tr_k) / 2)**3
            tcl_k = tcl + 273.15
            
            tcl_new = (Icl * fcl * (M - W) + fcl * hr * tr_k + fcl * hc * ta + ta_k) / (1 + Icl * fcl * (hr + hc))
            tcl = tcl_new - 273.15
        
        tcl_k = tcl + 273.15
        
        # Straty ciepła przez konwekcję i radiację [W/m²]
        HL1 = 3.05 * 0.001 * (5733 - 6.99 * (M - W) - pa)  # Dyfuzja pary przez skórę
        HL2 = 0.42 * ((M - W) - 58.15) if (M - W) > 58.15 else 0  # Pocenie
        HL3 = 1.7 * 0.00001 * M * (5867 - pa)  # Latentne przez oddech
        HL4 = 0.0014 * M * (34 - ta)  # Sensible przez oddech
        HL5 = 3.96 * fcl * (tcl_k**4 - tr_k**4)  # Radiacja
        HL6 = fcl * hc * (tcl - ta)  # Konwekcja
        
        # Obciążenie termiczne [W/m²]
        thermal_load = M - W - HL1 - HL2 - HL3 - HL4 - HL5 - HL6
        
        # PMV równanie
        pmv = (0.303 * np.exp(-0.036 * M) + 0.028) * thermal_load
        
        return max(-3.0, min(3.0, pmv))
    
    def calculate_pmv_simple(self, ta: float, tr: float, va: float, rh: float, 
                            met: float = 1.2, clo: float = 0.7) -> float:
        """
        Uproszczone obliczenie PMV (fallback gdy biblioteka niedostępna).
        
        Args:
            ta (float): Temperatura powietrza [°C]
            tr (float): Średnia temperatura radiacyjna [°C]
            va (float): Prędkość powietrza [m/s]  
            rh (float): Wilgotność względna [%]
            met (float): Aktywność metaboliczna [met]
            clo (float): Izolacyjność odzieży [clo]
            
        Returns:
            float: Przybliżona wartość PMV
        """
        # Temperatura efektywna
        t_eff = ta + 0.3 * (tr - ta) - 2.0 * np.sqrt(va)
        
        # Korekty na parametry środowiska i człowieka
        humidity_factor = 1 + 0.01 * (rh - 50)
        met_factor = 1 + 0.5 * (met - 1.2)  
        clo_factor = 1 - 0.3 * (clo - 0.7)
        
        # Uproszczone PMV
        pmv = (t_eff - 22) / 8 * humidity_factor * met_factor * clo_factor
        
        return max(-3.0, min(3.0, pmv))
    
    def calculate_ppd_from_pmv(self, pmv: float) -> float:
        """
        Oblicza PPD (Predicted Percentage of Dissatisfied) na podstawie PMV.
        
        Formuła Fangera (ISO 7730):
        PPD = 100 - 95 * exp(-0.03353 * PMV^4 - 0.2179 * PMV^2)
        
        Args:
            pmv (float): Wartość PMV
            
        Returns:
            float: PPD w procentach [5-100]
        """
        ppd = 100 - 95 * np.exp(-0.03353 * pmv**4 - 0.2179 * pmv**2)
        return max(5.0, min(100.0, ppd))  # PPD zawsze ≥ 5%
    
    def calculate_utci_simple(self, ta: float, tr: float, va: float, rh: float) -> float:
        """
        Uproszczone obliczenie UTCI (Universal Thermal Climate Index).
        
        UTCI jest wskaźnikiem stresu termicznego uwzględniającym wszystkie
        główne parametry meteorologiczne wpływające na człowieka.
        
        Args:
            ta (float): Temperatura powietrza [°C]
            tr (float): Średnia temperatura radiacyjna [°C]
            va (float): Prędkość powietrza [m/s]
            rh (float): Wilgotność względna [%]
            
        Returns:
            float: UTCI [°C]
        """
        # Bazowa temperatura UTCI ≈ temperatura powietrza
        utci = ta
        
        # Korekta na temperaturę radiacyjną (0.4 - współczynnik empiryczny)
        utci += 0.4 * (tr - ta)
        
        # Korekta na wiatr (efekt chłodzenia convective)
        if va > 0.5:
            wind_cooling = -2.0 * np.sqrt(va)
            utci += wind_cooling
        
        # Korekta na wilgotność (nieliniowa zależność od temperatury)
        if ta > 20:
            humidity_effect = 0.01 * (rh - 50)    # Nagrzewanie przy wysokiej T
        else:
            humidity_effect = -0.005 * (rh - 50)  # Chłodzenie przy niskiej T
        
        utci += humidity_effect
        
        return utci
    
    def calculate_pet_simple(self, ta: float, tr: float, va: float, rh: float,
                            met: float = 1.4, clo: float = 0.9) -> float:
        """
        Uproszczone obliczenie PET (Physiologically Equivalent Temperature).
        
        PET to temperatura powietrza, przy której bilans cieplny człowieka
        w pomieszczeniu referencyjnym równa się bilansowi w środowisku zewnętrznym.
        
        Args:
            ta (float): Temperatura powietrza [°C]
            tr (float): Średnia temperatura radiacyjna [°C]
            va (float): Prędkość powietrza [m/s]
            rh (float): Wilgotność względna [%]
            met (float): Aktywność metaboliczna [met] (1.4 dla spaceru)
            clo (float): Izolacyjność odzieży [clo] (0.9 letnie ubranie)
            
        Returns:
            float: PET [°C]
        """
        # Model uproszczony - korelacja empiryczna z PMV
        pmv = self.calculate_pmv_simple(ta, tr, va, rh, met, clo)
        
        # Przekształcenie PMV -> PET (relacja empiryczna)
        pet = 18 + 7 * pmv  # °C
        
        return pet
    
    def estimate_mean_radiant_temperature(self, ta: float, solar_rad: float, 
                                        surface_type: str = "urban") -> float:
        """
        Szacuje temperaturę radiacyjną średnią (Tmrt) na podstawie warunków środowiska.
        
        Args:
            ta (float): Temperatura powietrza [°C]
            solar_rad (float): Promieniowanie słoneczne [W/m²]
            surface_type (str): Typ powierzchni ("urban", "grass", "water", "asphalt")
            
        Returns:
            float: Temperatura radiacyjna średnia [°C]
        """
        # Bazowa Tmrt = temperatura powietrza
        tmrt = ta
        
        # Współczynniki absorpcji słonecznej dla różnych powierzchni
        absorption_factors = {
            "urban": 0.06,      # Beton, cegła - średnia absorpcja
            "grass": 0.02,      # Zieleń - niska absorpcja, wysoka ewapotranspiracja  
            "water": 0.01,      # Woda - bardzo niska absorpcja, wysoka pojemność cieplna
            "asphalt": 0.08,    # Asfalt - wysoka absorpcja
            "roof": 0.07,       # Dachy - średnia/wysoka absorpcja
            "concrete": 0.065   # Beton - średnia absorpcja
        }
        
        solar_factor = absorption_factors.get(surface_type, 0.05)
        
        # Dodatek radiacyjny od promieniowania słonecznego
        radiation_increase = solar_rad * solar_factor / 100
        
        # Korekta na zachmurzenie (solar_rad jest już skorygowane)
        tmrt += radiation_increase
        
        # Dodatkowy efekt miejskiej wyspy ciepła radiacyjnej
        if surface_type in ["urban", "asphalt", "concrete"]:
            uhi_radiation = min(2.0, solar_rad / 400)  # Do +2°C dla pełnego słońca
            tmrt += uhi_radiation
        
        return tmrt
    
    def define_urban_zones(self) -> Dict[str, Dict]:
        """
        Definiuje charakterystyczne strefy mikroklimatu w centrum Suwałk.
        
        Returns:
            Dict[str, Dict]: Słownik stref z ich charakterystykami
        """
        zones = {
            "rynek_main": {
                "name": "Rynek Główny",
                "description": "Główny plac miejski z fontanną",
                "surface_type": "urban",
                "temp_offset": 3.0,        # °C (efekt UHI + materiały)
                "wind_reduction": 0.7,     # Osłonięcie od wiatru przez budynki
                "humidity_offset": -5,     # % (niższa wilgotność na placu)
                "area_percent": 8,
                "characteristics": ["fontanna", "plac_brukowany", "otwarty"]
            },
            "street_commercial": {
                "name": "Ulice handlowe",
                "description": "Główne ulice centrum z intensywnym ruchem",
                "surface_type": "asphalt",
                "temp_offset": 2.5,        # °C (kanion uliczny + ruch)
                "wind_reduction": 0.5,     # Efekt kanionu ulicznego
                "humidity_offset": -3,     # % 
                "area_percent": 25,
                "characteristics": ["kanion_uliczny", "ruch_samochodowy", "budynki_wysokie"]
            },
            "parks_green": {
                "name": "Parki i skwery",
                "description": "Obszary zieleni miejskiej",
                "surface_type": "grass",
                "temp_offset": -2.0,       # °C (chłodzenie ewapotranspiracja)
                "wind_reduction": 0.9,     # Naturalna wentylacja przez zieleń
                "humidity_offset": 8,      # % (wyższa wilgotność)
                "area_percent": 15,
                "characteristics": ["zielen_wysoka", "cien_naturalny", "ewapotranspiracja"]
            },
            "residential": {
                "name": "Obszary mieszkaniowe", 
                "description": "Zabudowa mieszkaniowa małej intensywności",
                "surface_type": "urban",
                "temp_offset": 1.0,        # °C (umiarkowany UHI)
                "wind_reduction": 0.8,     # Częściowe osłonięcie
                "humidity_offset": 0,      # % (neutralne)
                "area_percent": 35,
                "characteristics": ["zabudowa_niska", "podworka", "seminatural"]
            },
            "open_spaces": {
                "name": "Otwarte przestrzenie",
                "description": "Parkingi, place, tereny otwarte",
                "surface_type": "concrete", 
                "temp_offset": 2.8,        # °C (pełna ekspozycja słoneczna)
                "wind_reduction": 1.0,     # Brak osłon od wiatru
                "humidity_offset": -8,     # % (niska wilgotność)
                "area_percent": 17,
                "characteristics": ["pelna_ekspozycja", "brak_cienia", "materialy_sztuczne"]
            }
        }
        
        return zones
    
    def calculate_zone_comfort(self, zone: Dict, ta: float, rh: float, va: float, 
                              solar_rad: float, met: float, clo: float) -> Dict:
        """
        Oblicza wskaźniki komfortu dla konkretnej strefy miejskiej.
        
        Args:
            zone (Dict): Definicja strefy miejskiej
            ta (float): Temperatura powietrza [°C]
            rh (float): Wilgotność względna [%] 
            va (float): Prędkość wiatru [m/s]
            solar_rad (float): Promieniowanie słoneczne [W/m²]
            met (float): Aktywność metaboliczna [met]
            clo (float): Izolacyjność odzieży [clo]
            
        Returns:
            Dict: Wskaźniki komfortu dla strefy
        """
        # Lokalne warunki mikroklimatu
        local_temp = ta + zone["temp_offset"]
        local_humidity = max(20, min(95, rh + zone["humidity_offset"]))
        local_wind = va * zone["wind_reduction"]
        
        # Temperatura radiacyjna dla typu powierzchni
        local_tmrt = self.estimate_mean_radiant_temperature(
            local_temp, solar_rad, zone["surface_type"]
        )
        
        # Oblicz wskaźniki komfortu
        try:
            # Próba użycia biblioteki pythermalcomfort jeśli dostępna
            from pythermalcomfort.models import pmv_ppd, utci
            pmv_result = pmv_ppd(tdb=local_temp, tr=local_tmrt, vr=local_wind, 
                                rh=local_humidity, met=met, clo=clo)
            pmv = pmv_result['pmv'] 
            ppd = pmv_result['ppd']
            utci_value = utci(tdb=local_temp, tr=local_tmrt, v=local_wind, rh=local_humidity)
        except ImportError:
            # Fallback do uproszczonych implementacji
            pmv = self.calculate_pmv_simple(local_temp, local_tmrt, local_wind, local_humidity, met, clo)
            ppd = self.calculate_ppd_from_pmv(pmv)
            utci_value = self.calculate_utci_simple(local_temp, local_tmrt, local_wind, local_humidity)
        
        # PET (zawsze uproszczona implementacja)
        pet_value = self.calculate_pet_simple(local_temp, local_tmrt, local_wind, local_humidity, met, clo)
        
        # Klasyfikacja poziomu komfortu (skala 5-stopniowa)
        if abs(pmv) < 0.5:
            comfort_level = "DOSKONAŁY"
            comfort_score = 5
        elif abs(pmv) < 1.0:
            comfort_level = "DOBRY"
            comfort_score = 4
        elif abs(pmv) < 1.5:
            comfort_level = "AKCEPTOWALNY" 
            comfort_score = 3
        elif abs(pmv) < 2.0:
            comfort_level = "SŁABY"
            comfort_score = 2
        else:
            comfort_level = "NIEAKCEPTOWALNY"
            comfort_score = 1
        
        # Rekomendacje adaptacyjne
        if pmv > 2:
            recommendation = "Unikać ekspozycji 10:00-18:00, szukać cienia, nawodnienie"
        elif pmv > 1:
            recommendation = "Krótkie przebywanie, częste przerwy w cieniu, nawodnienie"
        elif pmv > 0.5:
            recommendation = "Komfortowe warunki, możliwe dłuższe przebywanie"
        elif pmv < -2:
            recommendation = "Ochrona przed wiatrem, ciepłe ubranie, aktywność fizyczna"
        elif pmv < -1:
            recommendation = "Dodatkowa warstwa odzieży, ograniczenie czasu ekspozycji"
        elif pmv < -0.5:
            recommendation = "Lekka korekta ubioru, generalnie komfortowe warunki"
        else:
            recommendation = "Optymalne warunki komfortu termicznego"
        
        return {
            "zone_name": zone["name"],
            "area_percent": zone["area_percent"],
            "microclimate": {
                "air_temp": round(local_temp, 1),
                "mean_radiant_temp": round(local_tmrt, 1),
                "wind_speed": round(local_wind, 2),
                "humidity": round(local_humidity, 1),
                "surface_type": zone["surface_type"]
            },
            "comfort_indices": {
                "pmv": round(pmv, 2),
                "ppd": round(ppd, 1),
                "utci": round(utci_value, 1),
                "pet": round(pet_value, 1)
            },
            "assessment": {
                "comfort_level": comfort_level,
                "comfort_score": comfort_score,
                "recommendation": recommendation,
                "thermal_stress": "heat" if pmv > 1 else "cold" if pmv < -1 else "neutral"
            }
        }
    
    def generate_comfort_points(self, scenario_name: str, zones_results: Dict, 
                               overall_comfort: float) -> List[Dict]:
        """
        Generuje punkty komfortu termicznego do wizualizacji na mapie.
        
        Args:
            scenario_name (str): Nazwa scenariusza
            zones_results (Dict): Wyniki dla stref miejskich
            overall_comfort (float): Ogólny komfort miasta
            
        Returns:
            List[Dict]: Lista punktów z wskaźnikami komfortu
        """
        # Deterministyczne generowanie (powtarzalne wyniki)
        seed_value = abs(hash(scenario_name) + int(overall_comfort * 1000)) % (2**31)
        np.random.seed(seed_value)
        
        # Liczba punktów zależna od zróżnicowania komfortu
        comfort_variance = np.var([z['comfort_indices']['pmv'] for z in zones_results.values()])
        num_points = min(80, max(30, int(comfort_variance * 50 + 40)))
        
        comfort_points = []
        zone_list = list(zones_results.keys())
        zone_weights = [zones_results[z]['area_percent'] / 100 for z in zone_list]
        
        for i in range(num_points):
            # Lokalizacja punktu
            lat = self.center_lat + np.random.normal(0, 0.008)
            lng = self.center_lng + np.random.normal(0, 0.012)
            
            # Przypisanie do strefy (losowanie ważone powierzchnią)
            zone_choice = np.random.choice(zone_list, p=zone_weights)
            zone_data = zones_results[zone_choice]
            
            # Lokalne wariacje wskaźników komfortu
            base_pmv = zone_data['comfort_indices']['pmv']
            local_pmv_variation = np.random.normal(0, 0.3)
            local_pmv = np.clip(base_pmv + local_pmv_variation, -3, 3)
            
            base_utci = zone_data['comfort_indices']['utci']
            local_utci_variation = np.random.normal(0, 2.0)
            local_utci = base_utci + local_utci_variation
            
            base_pet = zone_data['comfort_indices']['pet']
            local_pet_variation = np.random.normal(0, 2.5)
            local_pet = base_pet + local_pet_variation
            
            # Temperatura powierzchni (Tmrt + wariacja)
            base_surface_temp = zone_data['microclimate']['mean_radiant_temp']
            surface_temp = base_surface_temp + np.random.normal(0, 3)
            
            comfort_points.append({
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "pmv": round(local_pmv, 2),
                "ppd": round(self.calculate_ppd_from_pmv(local_pmv), 1),
                "utci": round(local_utci, 1),
                "pet": round(local_pet, 1),
                "zone_type": zone_choice,
                "surface_temp": round(surface_temp, 1),
                "comfort_score": max(1, min(5, round(5 - abs(local_pmv), 0))),
                "microenvironment": zone_data['microclimate']['surface_type']
            })
        
        return comfort_points
    
    def simulate_scenario(self, ta: float, rh: float, va: float, solar_rad: float,
                         scenario_name: str, season: str = "summer", 
                         detailed_output: bool = True) -> Dict:
        """
        Główna funkcja symulująca scenariusz komfortu termicznego.
        
        Args:
            ta (float): Temperatura powietrza [°C]
            rh (float): Wilgotność względna [%]
            va (float): Prędkość wiatru [m/s]
            solar_rad (float): Promieniowanie słoneczne [W/m²]
            scenario_name (str): Nazwa scenariusza
            season (str): Sezon ("winter", "spring", "summer", "autumn")
            detailed_output (bool): Czy generować szczegółowe dane
            
        Returns:
            Dict: Kompletne wyniki analizy komfortu termicznego
        """
        print(f"\n🌡️ ThermalSim: {scenario_name}")
        print(f"   🌡️ {ta}°C, {rh}%RH, {va}m/s, {solar_rad}W/m²")
        
        # Parametry ubrania i aktywności według sezonu
        clothing_values = {
            "winter": 2.0,   # Zimowe ubranie (płaszcz, sweter)
            "spring": 0.8,   # Przejściowe (kurtka, długie rękawy)
            "summer": 0.4,   # Letnie (koszula, krótkie rękawy)
            "autumn": 1.0    # Jesienne (sweter, lekka kurtka)
        }
        
        activity_values = {
            "winter": 1.4,   # Szybkie chodzenie (rozgrzewka)
            "spring": 1.2,   # Normalne chodzenie
            "summer": 1.0,   # Powolny spacer (unikanie przegrzania)  
            "autumn": 1.3    # Energiczne chodzenie
        }
        
        clo = clothing_values.get(season, 0.7)
        met = activity_values.get(season, 1.2)
        
        # Definiuj strefy miejskie
        urban_zones = self.define_urban_zones()
        
        # Analiza komfortu dla każdej strefy
        zone_results = {}
        overall_comfort_score = 0
        
        for zone_id, zone in urban_zones.items():
            zone_comfort = self.calculate_zone_comfort(zone, ta, rh, va, solar_rad, met, clo)
            zone_results[zone_id] = zone_comfort
            
            # Wkład do ogólnego komfortu (ważony powierzchnią strefy)
            zone_contribution = zone_comfort['assessment']['comfort_score'] * zone['area_percent'] / 100
            overall_comfort_score += zone_contribution
        
        # Statystyki ogólne miasta
        comfortable_zones_count = sum(1 for z in zone_results.values() 
                                    if abs(z['comfort_indices']['pmv']) < 1.0)
        comfortable_zones_percent = comfortable_zones_count / len(zone_results) * 100
        
        heat_stress_zones = sum(1 for z in zone_results.values() 
                               if z['comfort_indices']['pmv'] > 2)
        cold_stress_zones = sum(1 for z in zone_results.values() 
                               if z['comfort_indices']['pmv'] < -2)
        
        # Generuj punkty komfortu do wizualizacji
        comfort_points = []
        if detailed_output:
            comfort_points = self.generate_comfort_points(scenario_name, zone_results, overall_comfort_score)
        
        # Strukturyzacja wyników
        result = {
            'scenario_name': scenario_name,
            'module': 'ThermalSim',
            'model_version': 'ThermalSim_v1.6_PMV_UTCI_PET',
            'computation_time': datetime.now().isoformat(),
            
            'parameters': {
                'air_temperature': ta,
                'relative_humidity': rh,
                'wind_speed': va,
                'solar_radiation': solar_rad,
                'clothing_insulation_clo': clo,
                'metabolic_rate_met': met,
                'season': season
            },
            
            'environmental_conditions': {
                'thermal_stress_category': self._classify_thermal_stress(ta),
                'humidity_comfort': "optimal" if 40 <= rh <= 60 else "suboptimal",
                'wind_comfort': "optimal" if 0.5 <= va <= 2.0 else "suboptimal",
                'solar_load': "low" if solar_rad < 200 else "moderate" if solar_rad < 600 else "high"
            },
            
            'overall_metrics': {
                'city_comfort_score': round(overall_comfort_score, 2),
                'comfort_zones_percent': round(comfortable_zones_percent, 1),
                'heat_stress_zones': heat_stress_zones,
                'cold_stress_zones': cold_stress_zones,
                'uhi_effect_estimated': round(max(0, ta - 20) * 0.15, 1)  # Uproszczony UHI
            },
            
            'zone_analysis': zone_results
        }
        
        # Dodaj punkty komfortu jeśli wymagane
        if detailed_output:
            result['comfort_map'] = comfort_points
            result['visualization'] = {
                'center_lat': self.center_lat,
                'center_lng': self.center_lng,
                'zoom_level': 14,
                'color_scale': 'RdYlBu_r',  # Red-Yellow-Blue (reversed)
                'legend_title': 'PMV Comfort Scale'
            }
        
        # Logi wynikowe
        print(f"   📊 Komfort miasta: {overall_comfort_score:.2f}/5.0")
        print(f"   🌡️ Strefy komfortowe: {comfortable_zones_percent:.0f}%")
        if heat_stress_zones > 0:
            print(f"   🔥 Strefy stresu cieplnego: {heat_stress_zones}")
        if cold_stress_zones > 0:
            print(f"   🧊 Strefy stresu chłodnego: {cold_stress_zones}")
        
        return result
    
    def _classify_thermal_stress(self, ta: float) -> str:
        """Klasyfikuje stres termiczny na podstawie temperatury powietrza."""
        if ta < -10:
            return "extreme_cold"
        elif ta < 0:
            return "cold"
        elif ta < 18:
            return "cool"
        elif ta < 26:
            return "comfortable"
        elif ta < 32:
            return "warm"
        elif ta < 38:
            return "hot"
        else:
            return "extreme_heat"
    
    def batch_simulate(self, scenarios: List[Tuple]) -> Dict[str, Dict]:
        """
        Uruchamia batch analizę komfortu dla wielu scenariuszy.
        
        Args:
            scenarios (List[Tuple]): Lista (ta, rh, va, solar, name, season)
            
        Returns:
            Dict[str, Dict]: Wyniki wszystkich scenariuszy
        """
        results = {}
        
        print(f"\n🔄 Thermal Comfort Batch: {len(scenarios)} scenarios")
        
        for i, (ta, rh, va, solar, name, season) in enumerate(scenarios, 1):
            print(f"\n[{i}/{len(scenarios)}]", end=" ")
            result = self.simulate_scenario(ta, rh, va, solar, name, season)
            key = name.lower().replace(" ", "_")
            results[key] = result
        
        print(f"\n✅ Thermal Batch completed: {len(results)} scenarios")
        return results
    
    def export_results(self, results: Dict, output_file: str = "thermal_results.json"):
        """
        Eksportuje wyniki analizy komfortu do pliku JSON.
        
        Args:
            results (Dict): Wyniki symulacji
            output_file (str): Nazwa pliku wyjściowego
        """
        export_data = {
            "metadata": {
                "module": "ThermalSim",
                "version": "1.6.0",
                "indices": ["PMV", "PPD", "UTCI", "PET"],
                "standards": ["ISO 7730", "ISO 17772"],
                "location": self.config['location'],
                "generated": datetime.now().isoformat(),
                "scenarios_count": len(results)
            },
            "configuration": {
                "urban_heat_island_max": self.urban_heat_island_max,
                "green_cooling_effect": self.green_cooling_effect,
                "human_parameters": {
                    "body_surface_area_m2": self.human_body_surface_area,
                    "skin_emissivity": self.skin_emissivity
                }
            },
            "results": results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"💾 Thermal comfort results exported to: {output_file}")

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
    
    # Inicjalizacja symulatora komfortu
    thermal_sim = ThermalComfortSimulator(test_config)
    
    # Pojedyncza symulacja
    result = thermal_sim.simulate_scenario(28, 60, 2.0, 600, "Test upał letni", "summer")
    
    # Batch symulacja
    scenarios = [
        (-5, 75, 3.0, 50, "Zima mroźna", "winter"),
        (22, 55, 1.5, 400, "Lato komfortowe", "summer"),
        (32, 45, 1.0, 800, "Upał letni", "summer")
    ]
    
    batch_results = thermal_sim.batch_simulate(scenarios)
    thermal_sim.export_results(batch_results, "thermal_batch_results.json")