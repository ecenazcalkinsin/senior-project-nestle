import pandas as pd
import sqlite3


class Database:
    def __init__(self, db_path, **kwargs) -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, **kwargs)
        self.cursor = self.conn.cursor()

    def _parse_coordinates(self, data):
        name, coordinates = data
        x, y = coordinates.split(",")
        return name, float(x), float(y)

    def get_machine_names(self):
        self.cursor.execute("SELECT LokasyonAdı FROM full_machines")
        data = self.cursor.fetchall()
        return [x[0] for x in data]

    def get_coordinates(self):
        self.cursor.execute("SELECT LokasyonAdı, GPS FROM full_machines")
        data = self.cursor.fetchall()
        data = list(map(self._parse_coordinates, data))
        return pd.DataFrame(data, columns=["name", "x", "y"])

    def get_all_machines(self):
        self.cursor.execute("SELECT LokasyonAdı FROM all_machines")
        data = self.cursor.fetchall()
        return [x[0] for x in data]

    def get_forecast(self):
        self.cursor.execute("SELECT * FROM FORECAST")
        data = self.cursor.fetchall()
        return pd.DataFrame(data, columns=["date", "machine", "ingredient", "value"])

    def get_forecast_for_machine(self, machine_name):
        self.cursor.execute("SELECT * FROM FORECAST WHERE machine = ?", (machine_name,))
        data = self.cursor.fetchall()
        return pd.DataFrame(data, columns=["date", "machine", "ingredient", "value"])

    def get_forecast_by_cluster(self):
        forecasts = self.get_forecast()
        machines = forecasts["machine"].unique()  # Get this to cluster
        forecasts_by_machine = {
            machine: self.get_forecast_for_machine(machine) for machine in machines
        }
        forecasts_by_machine_by_ingredient = {
            machine: [
                df[df["ingredient"] == ingredient]["value"].tolist()
                for ingredient in sorted(df["ingredient"].unique())
            ]
            for machine, df in forecasts_by_machine.items()
        }
        forecasts_by_machine_by_ingredient = dict(
            sorted(forecasts_by_machine_by_ingredient.items(), reverse=True)
        )
        names = list(forecasts_by_machine_by_ingredient.keys())
        values = list(forecasts_by_machine_by_ingredient.values())
        return names, values
