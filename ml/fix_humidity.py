import pandas as pd
import numpy as np
import os

def dewpoint_k_to_rh(temp_c, dewpoint_k):
    Td = dewpoint_k - 273.15  # Kelvin -> Celsius
    a, b = 17.625, 243.04
    es = np.exp((a * Td) / (b + Td))
    e = np.exp((a * temp_c) / (b + temp_c))
    rh = 100 * es / e
    return rh.clip(lower=0, upper=100)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'datasets', 'dataset.csv')
    out_path = os.path.join(script_dir, 'datasets', 'dataset_fixed.csv')
    
    print(f"Loading dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    print("Initial Humidity Stats:")
    print(df['Humidity'].describe())
    
    bad_mask = df['Humidity'] > 100
    bad_count = bad_mask.sum()
    print(f"Rows to fix (Humidity > 100): {bad_count} ({bad_count / len(df) * 100:.2f}%)")
    
    # Magnus conversion
    df.loc[bad_mask, 'Humidity'] = dewpoint_k_to_rh(
        df.loc[bad_mask, 'Temperature'],
        df.loc[bad_mask, 'Humidity']
    )
    
    print("\nFixed Humidity Stats:")
    print(df['Humidity'].describe())
    
    # Validation checks
    assert df['Humidity'].min() >= 0.0, "Minimum humidity is less than 0%"
    assert df['Humidity'].max() <= 100.0, "Maximum humidity is greater than 100%"
    assert len(df) == 381060, f"Row count changed: {len(df)} (expected 381060)"
    
    print(f"Saving fixed dataset to {out_path}...")
    df.to_csv(out_path, index=False)
    print("Dataset saved successfully.")

if __name__ == '__main__':
    main()
