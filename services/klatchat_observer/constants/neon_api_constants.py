from enum import Enum
from typing import Dict, List


class NeonServices(Enum):
    OWM = 'open_weather_map'
    WOLFRAM = 'wolfram_alpha'
    ALPHA_VANTAGE = 'alpha_vantage'


neon_service_tokens: Dict[NeonServices, List[str]] = {
    NeonServices.OWM: ['lat', 'lng', 'lon'],
    NeonServices.ALPHA_VANTAGE: ['symbol'],
    NeonServices.WOLFRAM: ['query']
}