import pandas as pd
import matplotlib.pyplot as plt
df = pd.read_csv(r"D:\COLLEGE\stock.txt")
plt.plot(df['Date'], df['Open'], marker='o')
plt.xlabel('Date')
plt.ylabel('Open Price')
plt.grid(True)
plt.show()

