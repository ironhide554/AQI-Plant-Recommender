from pydantic import BaseModel, Field

class Data(BaseModel):
    PM2_5: float = Field(..., alias='PM2.5')
    PM10: float = Field(..., alias='PM10')
    NO: float = Field(..., alias='NO')
    NO2: float = Field(..., alias='NO2')
    NOx: float = Field(..., alias='NOx')
    NH3: float = Field(..., alias='NH3')
    CO: float = Field(..., alias='CO')
    SO2: float = Field(..., alias='SO2')
    O3: float = Field(..., alias='O3')
    Benzene: float = Field(..., alias='Benzene')
    Toluene: float = Field(..., alias='Toluene')
    Xylene: float = Field(..., alias='Xylene')
    AQI: float = Field(..., alias='AQI')
