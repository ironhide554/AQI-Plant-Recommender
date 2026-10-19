from pydantic import BaseModel, Field, ConfigDict

class Data(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    PM2_5: float = Field(..., alias='PM2.5')
    PM10: float
    NO: float
    NO2: float
    NOx: float
    NH3: float
    CO: float
    SO2: float
    O3: float
    Benzene: float
    Toluene: float
    Xylene: float
    AQI: float
