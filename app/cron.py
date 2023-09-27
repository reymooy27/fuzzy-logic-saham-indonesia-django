from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import os
from .models import Price, Stock



def cron_job():
    element = ''
    data = []
    stock_symbol = 'ANTM'
    stock_data = Stock.objects.filter(code=stock_symbol)
    print(stock_data)
    # stop_date = 'Sep 20, 2023'
    # url = f'https://finance.yahoo.com/quote/{stock_symbol}.JK/history?p={stock_symbol}.JK'
    # path = os.path.join(os.path.dirname(__file__), 'chromedriver.exe')
    # driver = webdriver.Chrome(executable_path=path)
    # driver.get(url)
    # elements = WebDriverWait(driver, 10).until(
    #     EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.BdT'))
    # )
    # for element in elements:
    #     row = element.find_elements(By.TAG_NAME, 'td')
    #     if len(row) >= 5:
    #         print(row[2].text)
    #         date = row[0].text
    #         open_price = row[1].text
    #         high_price = row[2].text
    #         low_price = row[3].text
    #         close_price = row[4].text
    #         volume = row[6].text

    #         price_instance = Price(
    #             stock=stock_data.,  # Replace with your Stock instance
    #             date=date,
    #             open=open_price,
    #             high=high_price,
    #             low=low_price,
    #             close=close_price,
    #             volume=volume
    #         )

    #         # Save the instance to the database
    #         price_instance.save()
    #         print(f"Saved data for date: {date}")

    #         if date == stop_date:
    #             print("Reached stop date. Exiting the loop.")
    #             break
    #     else:
    #         print("Row < 5")

    # print(data)
    # df = pd.DataFrame(data, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
    # df['Open'] = df['Open'].str.replace(',', '').astype(float)
    # df['High'] = df['High'].str.replace(',', '').astype(float)
    # df['Low'] = df['Low'].str.replace(',', '').astype(float)
    # df['Close'] = df['Close'].str.replace(',', '').astype(float)
    # print(df)