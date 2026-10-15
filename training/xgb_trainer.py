import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.loader import DataLoader





if __name__ == "__main__":
    dl = DataLoader()
    df = dl.get_training_data()
    print(df.head(n=50))
