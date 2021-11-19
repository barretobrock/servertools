from typing import List


class Plant:
    def __init__(self, name: str, temp_min: float, temp_max: float, is_outdoor: bool = True):
        self.name = name
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.is_outdoor = is_outdoor

    def __repr__(self) -> str:
        return f'<Plant(name="{self.name}")>'


class Plants:
    FLEX_C = 2  # Flexibility in the lowest allowable temperature
    PLANTS = [
        Plant('blue_echeveria', 10, 35),
        Plant('blue_fescue', -10, 35),
        Plant('catnip_big', 5, 25),
        Plant('catnip_small', 5, 25),
        Plant('common_ivy', 10, 20, is_outdoor=False),
        Plant('creeping_fig_big', 16, 30),
        Plant('creeping_fig_small', 16, 30),
        Plant('dill', 15, 21),
        Plant('firebush', 18, 35),
        Plant('golden_barrel', 10, 35),
        Plant('golden_cereus', 10, 35),
        Plant('mammillaria_mystax', 10, 35),
        Plant('mexican_feathergrass', 5, 35),
        Plant('monstrose_apple', 10, 35),
        Plant('panda_plant', 10, 35),
        Plant('pink_muhly', 15, 25),
        Plant('rose', 5, 25),
        Plant('mint', 10, 21),
        Plant('tree_cactus', 12, 35),
        Plant('turks_head', 10, 35)
    ]

    def __init__(self):
        self.plants = []    # type: List[Plant]
        self.add_plants(self.PLANTS)

    def add_plant(self, plant: Plant):
        self.plants.append(plant)

    def add_plants(self, plantlist: List[Plant]):
        for plant in plantlist:
            self.add_plant(plant)

    def get_cold_plants(self, temp: float) -> List[Plant]:
        """Returns a list of plants whose min temp threshold is above the marked low temp"""
        return [x for x in self.plants if (x.temp_min - self.FLEX_C) >= temp]

    def get_hot_plants(self, temp: float) -> List[Plant]:
        """Returns a list of plants whose max temp threshold is below the marked high temp"""
        return [x for x in self.plants if (x.temp_max - self.FLEX_C) >= temp]

    def get_min_temp(self) -> float:
        """Gets the minimum threshold temp from the plants stored"""
        return min([x.temp_min for x in self.plants])

    def get_max_temp(self) -> float:
        """Gets the maximum threshold temp from the plants stored"""
        return max([x.temp_max for x in self.plants])
