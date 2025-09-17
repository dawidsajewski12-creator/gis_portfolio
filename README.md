# 🌍 GIS Microclimate Platform - Suwałki

**System Analiz Środowiskowych dla centrum miasta Suwałki**

[![Environmental Analysis](https://img.shields.io/badge/Environmental-Analysis-green)](https://github.com/dawidsajewski12-creator/gis_portfolio)
[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📍 Lokalizacja

- **Miasto**: Suwałki, Polska  
- **Współrzędne**: 54.10°N, 22.95°E
- **Obszar analizy**: 5 km² centrum miasta
- **Rozdzielczość**: 5m × 5m (1,280,000 komórek)

## 🚀 Moduły Systemu

### 🌊 FloodSim - Symulacje Powodzi
- **Model**: Hydrauliczny 2D Saint-Venant
- **Scenariuszy**: 6
- **Zakres opadów**: 15-220 mm/h
- **Parametry**: Głębokość zalewu, obszar, budynki zagrożone

### 💨 WindSim - Analiza Wiatru  
- **Model**: CFD uproszczony z efektami miejskimi
- **Scenariuszy**: 5
- **Zakres wiatru**: 5-35 m/s
- **Parametry**: Prędkość, kierunek, komfort pieszych

### 🌡️ ThermalSim - Komfort Termiczny
- **Wskaźniki**: PMV, PPD, UTCI (ISO 7730, ISO 17772)
- **Scenariuszy**: 6 
- **Zakres temperatur**: -5°C do +38°C
- **Parametry**: Komfort strefy, mikroklima miejski

## 📊 Aktualne Wyniki

**Ostatnia aktualizacja**: 2025-09-17 05:33:16

### 🌊 Największe Zagrożenia Powodziowe
- **Max głębokość**: 0.612 m
- **Scenariuszy wysokiego ryzyka**: 3

### 💨 Analiza Wiatru
- **Max prędkość**: 42.0 m/s
- **Obszary niskiego komfortu**: 4

### 🌡️ Komfort Termiczny
- **Najlepszy komfort**: 4.8/5.0
- **Najgorszy komfort**: 2.0/5.0

## 🗂️ Struktura Danych

```
api/data/
├── environmental_data.json     # Kompletne wyniki
├── flood_scenarios.json        # Scenariusze powodzi
├── wind_scenarios.json         # Scenariusze wiatru  
├── thermal_scenarios.json      # Scenariusze komfortu
├── flood_zones.geojson         # Punkty zalewów (mapa)
├── wind_field.geojson          # Pole wiatru (mapa)
└── thermal_comfort.geojson     # Komfort termiczny (mapa)
```

## 🛠️ API Endpoints

```bash
# Wszystkie dane
GET https://raw.githubusercontent.com/dawidsajewski12-creator/gis_portfolio/main/api/data/environmental_data.json

# Moduł powodzi
GET https://raw.githubusercontent.com/dawidsajewski12-creator/gis_portfolio/main/api/data/flood_scenarios.json

# Moduł wiatru
GET https://raw.githubusercontent.com/dawidsajewski12-creator/gis_portfolio/main/api/data/wind_scenarios.json

# Moduł komfortu
GET https://raw.githubusercontent.com/dawidsajewski12-creator/gis_portfolio/main/api/data/thermal_scenarios.json
```

## 🎨 Frontend Integration

### React Components
```jsx
import { useEnvironmentalData } from './hooks/useEnvironmentalData';

const SuwalkinMap = () => {
  const { floodData, windData, thermalData } = useEnvironmentalData();
  
  return (
    <MapContainer center={[54.10, 22.95]} zoom={14}>
      <FloodLayer data={floodData} />
      <WindLayer data={windData} />
      <ThermalLayer data={thermalData} />
    </MapContainer>
  );
};
```

### Example Usage
```javascript
// Pobierz dane powodzi
fetch('https://raw.githubusercontent.com/dawidsajewski12-creator/gis_portfolio/main/api/data/flood_scenarios.json')
  .then(response => response.json())
  .then(data => {
    console.log('Flood scenarios:', data);
  });
```

## 🔧 Uruchomienie w Google Colab

1. Otwórz notebook: `notebooks/environmental_analysis_main.py`
2. Ustaw GitHub token
3. Uruchom wszystkie komórki
4. Wyniki automatycznie trafią do tego repozytorium

## 📈 Technologie

- **Backend**: Python 3.8+, NumPy, Pandas, scikit-learn
- **GIS**: GeoPandas, Shapely, Folium
- **ML**: Random Forest, Gradient Boosting
- **API**: GitHub Pages, JSON/GeoJSON
- **Frontend**: React, Leaflet, D3.js

## 👥 Zespół

- **Environmental Analytics Team**
- **Kontakt**: environmental.analytics@suwalki.pl
- **GitHub**: @dawidsajewski12-creator

## 📄 Licencja

MIT License - Zobacz [LICENSE](LICENSE) dla szczegółów.

---

**🌱 Zrównoważony rozwój miast poprzez analizy środowiskowe**
