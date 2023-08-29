from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import os

element = ''
data = []
stock_symbol = 'BBCA'
url = f'https://finance.yahoo.com/quote/{stock_symbol}.JK/history?p={stock_symbol}.JK'
path = os.path.join(os.path.dirname(__file__), 'chromedriver.exe')
driver = webdriver.Chrome(executable_path=path)
driver.get(url)
elements = WebDriverWait(driver, 10).until(
    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.BdT'))
)
for element in elements:
    row = element.find_elements(By.CSS_SELECTOR, 'td.Py\(10px\)')
    if(row[0].text.startswith('Aug 16, 2023')):
        date = row[0].text
        open_price = row[1].text
        high_price = row[2].text
        low_price = row[3].text
        close_price = row[4].text
        volume = row[6].text
        data.append({date, open_price, high_price, low_price, close_price, volume})

print(data)
df = pd.DataFrame(data, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
df['Open'] = df['Open'].str.replace(',', '').astype(float)
df['High'] = df['High'].str.replace(',', '').astype(float)
df['Low'] = df['Low'].str.replace(',', '').astype(float)
df['Close'] = df['Close'].str.replace(',', '').astype(float)
print(df)