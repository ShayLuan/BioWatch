import csv
from datetime import datetime, timedelta
import random

# Configuration
CSV_FILENAME = "esp32_sensor_data.csv"
NUM_READINGS = 100
INTERVAL_SECONDS = 5  # Time between readings

# Sensor data ranges
TEMP_MIN = 15.0
TEMP_MAX = 35.0
TEMP_VARIATION = 0.5  # Max change between readings

TURBIDITY_MIN = 100
TURBIDITY_MAX = 800
TURBIDITY_VARIATION = 20  # Max change between readings

def generate_sensor_data(num_readings):
    """Generate simulated ESP32 sensor readings."""
    data = []
    
    # Initialize starting values
    current_temp = random.uniform(TEMP_MIN, TEMP_MAX)
    current_turbidity = random.uniform(TURBIDITY_MIN, TURBIDITY_MAX)
    
    # Starting timestamp
    timestamp = datetime.now()
    
    for i in range(num_readings):
        # Simulate gradual temperature changes with small random fluctuations
        temp_change = random.uniform(-TEMP_VARIATION, TEMP_VARIATION)
        current_temp = max(TEMP_MIN, min(TEMP_MAX, current_temp + temp_change))
        
        # Simulate gradual turbidity changes with small random fluctuations
        turbidity_change = random.uniform(-TURBIDITY_VARIATION, TURBIDITY_VARIATION)
        current_turbidity = max(TURBIDITY_MIN, min(TURBIDITY_MAX, current_turbidity + turbidity_change))
        
        # Create data record
        record = {
            "timestamp": timestamp.isoformat(),
            "temperature_c": round(current_temp, 2),
            "turbidity_ntu": round(current_turbidity, 2)
        }
        
        data.append(record)
        
        # Increment timestamp
        timestamp += timedelta(seconds=INTERVAL_SECONDS)
    
    return data

def save_to_csv(data, filename):
    """Save sensor data to CSV file."""
    if not data:
        print("No data to save.")
        return
    
    try:
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = ["timestamp", "temperature_c", "turbidity_ntu"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # Write header
            writer.writeheader()
            
            # Write data rows
            writer.writerows(data)
        
        print(f"✓ Successfully saved {len(data)} readings to '{filename}'")
    except IOError as e:
        print(f"✗ Error writing to file: {e}")

def main():
    """Main function."""
    print("Simulating ESP32 Sensor Data...")
    print(f"Generating {NUM_READINGS} readings at {INTERVAL_SECONDS}-second intervals\n")
    
    # Generate simulated data
    sensor_data = generate_sensor_data(NUM_READINGS)
    
    # Display first few records
    print("Sample of generated data:")
    for record in sensor_data[:5]:
        print(f"  {record}")
    print(f"  ...\n")
    
    # Save to CSV
    save_to_csv(sensor_data, f"simulation/{CSV_FILENAME}")
    
    # Display summary statistics
    temps = [d["temperature_c"] for d in sensor_data]
    turbidities = [d["turbidity_ntu"] for d in sensor_data]
    
    print("\nSummary Statistics:")
    print(f"  Temperature: {min(temps):.2f}°C to {max(temps):.2f}°C (avg: {sum(temps)/len(temps):.2f}°C)")
    print(f"  Turbidity: {min(turbidities):.2f} NTU to {max(turbidities):.2f} NTU (avg: {sum(turbidities)/len(turbidities):.2f} NTU)")

if __name__ == "__main__":
    main()
