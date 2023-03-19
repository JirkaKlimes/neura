import geocoder
from abc import ABC, abstractmethod
import json

class Location(ABC):
    def __init__(self) -> None:    
        lat = None
        lng = None
        city = None
        address = None
        country_code = None
        self.update()

    def __str__(self):
        lines = [
            f"Latitude: {self.lat}",
            f"Longitude: {self.lng}",
            f"City: {self.city}",
            f"Address: {self.address}",
            f"Coutnry Code: {self.country_code}"
        ]
        return "\n".join(lines)

    def __repr__(self):
        return str(self).replace("\n", " ")

    @abstractmethod
    def update(self): ...


class IPLocation(Location):
    def update(self):
        g = geocoder.ip('me')
        self.lat, self.lng = g.latlng
        self.city = g.city
        self.address = g.address
        self.country_code = g.country.lower()


if __name__ == "__main__":
    location = IPLocation()
    print(location)