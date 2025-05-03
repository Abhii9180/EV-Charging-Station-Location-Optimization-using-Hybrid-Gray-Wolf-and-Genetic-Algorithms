import psycopg2
import numpy as np
import random
from math import radians, sin, cos, sqrt, atan2

# Database connection
def get_db_connection():
    try:
        return psycopg2.connect(
            dbname="EV_STATIONS",
            user="postgres",
            password="Abhii@9180",
            host="localhost",
            port="5432"
        )
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        return None

# Haversine formula to calculate distance (in km)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  
    dlat = radians(lat2 - lat1)
    dlon = radians(lat2 - lon2)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

# Fetch existing EV stations
def get_existing_ev_stations():
    conn = get_db_connection()
    if not conn:
        return []

    cur = conn.cursor()
    cur.execute("SELECT id, name, latitude, longitude, type FROM ev_stations")
    stations = cur.fetchall()
    cur.close()
    conn.close()

    return [(row[0], row[1], row[2], row[3], row[4]) for row in stations]

# Fetch potential locations
def get_potential_locations(current_lat, current_lon):
    conn = get_db_connection()
    if not conn:
        return []

    cur = conn.cursor()
    cur.execute("SELECT id, name, latitude, longitude, type FROM potential_locations")
    locations = cur.fetchall()
    cur.close()
    conn.close()

    filtered_locations = [
        (row[0], row[1], row[2], row[3], row[4])
        for row in locations if haversine(current_lat, current_lon, row[2], row[3]) <= 100
    ]

    if not filtered_locations:
        print("No suitable potential locations found within 100 km.")
    
    return filtered_locations

# Genetic Algorithm for optimization
def genetic_algorithm(potential_locations, existing_stations, population_size=20, generations=50):
    if not potential_locations:
        print("Genetic algorithm skipped: No potential locations available.")
        return []

    def fitness(chromosome):
        return sum(1 for i in range(len(chromosome)) if chromosome[i] == 1 and 
                   all(haversine(potential_locations[i][2], potential_locations[i][3], ex_lat, ex_lon) > 5 
                       for _, _, ex_lat, ex_lon, _ in existing_stations))

    population = [np.random.choice([0, 1], size=len(potential_locations)).tolist() for _ in range(population_size)]
    
    for _ in range(generations):
        scores = [fitness(ind) for ind in population]
        sorted_population = [x for _, x in sorted(zip(scores, population), key=lambda pair: pair[0], reverse=True)]
        new_population = sorted_population[:population_size//2]

        while len(new_population) < population_size:
            parent1, parent2 = random.sample(sorted_population[:10], 2)
            if len(parent1) <= 1:  # Avoid invalid crossover
                continue

            crossover = random.randint(0, max(1, len(parent1)-1))  # FIXED crossover issue
            child = parent1[:crossover] + parent2[crossover:]

            if random.random() < 0.1 and child:  # Ensure mutation is valid
                mutate_index = random.randint(0, len(child)-1)
                child[mutate_index] = 1 - child[mutate_index]

            new_population.append(child)
        
        population = new_population

    return [potential_locations[i] for i in range(len(population[0])) if population[0][i] == 1]

# Store optimal locations
def store_optimal_locations(optimal_locations, existing_stations):
    if not optimal_locations:
        print("No optimal locations found to store.")
        return

    conn = get_db_connection()
    if not conn:
        return

    cur = conn.cursor()
    cur.execute("DELETE FROM optimal_ev_stations")

    for loc in optimal_locations + existing_stations:
        cur.execute(
            """
            INSERT INTO optimal_ev_stations (id, name, latitude, longitude, type)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (loc[0], loc[1], loc[2], loc[3], loc[4])
        )

    conn.commit()
    cur.close()
    conn.close()

# Main function
def find_and_store_optimal_stations(current_lat, current_lon):
    existing_stations = get_existing_ev_stations()
    potential_locations = get_potential_locations(current_lat, current_lon)

    optimal_ga_stations = genetic_algorithm(potential_locations, existing_stations)

    if optimal_ga_stations:
        store_optimal_locations(optimal_ga_stations, existing_stations)
        print(f"Stored {len(optimal_ga_stations) + len(existing_stations)} optimal EV stations successfully!")
    else:
        print("No optimal EV stations were found.")

# Example usage
if __name__ == "__main__":
    current_latitude = 26.08067
    current_longitude = 91.55810
    find_and_store_optimal_stations(current_latitude, current_longitude)
