from app.models import Stock, Price
import logging
from django.db import transaction
from celery import shared_task, Celery
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from stock_api.celery import app


def scrape_stock_data(stock_symbol):
    msg = ''

    try:
        # Retrieve the Stock instance based on the stock symbol
        stock_data = Stock.objects.get(code=stock_symbol)
        
        # Get the last recorded date for the specific stock
        last_price = Price.objects.filter(stock=stock_data).latest('date')
        stop_date = last_price.date.strftime('%b %d, %Y')
        
        # Define the URL and set up the webdriver
        url = f'https://finance.yahoo.com/quote/{stock_symbol}.JK/history?p={stock_symbol}.JK'
        path = os.path.join(os.path.dirname(__file__), 'chromedriver.exe')
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Use headless browser
        driver = webdriver.Chrome(executable_path=path, options=options)
        driver.get(url)
        
        # Scrape data
        elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'tr.BdT'))
        )
        
        for element in elements:
            row = element.find_elements(By.TAG_NAME, 'td')
            if last_price.date.strftime('%b %d, %Y') == row[0].text:
                msg = 'Data sudah paling baru'
                break

            if len(row) >= 5:
                date = row[0].text
                open_price = float(row[1].text.replace(',', ''))
                high_price = float(row[2].text.replace(',', ''))
                low_price = float(row[3].text.replace(',', ''))
                close_price = float(row[4].text.replace(',', ''))
                volume = int(row[6].text.replace(',', ''))

                # Create the Price instance and save it to the database within a transaction
                with transaction.atomic():
                    price_instance = Price(
                        stock=stock_data,
                        date=datetime.strptime(date, '%b %d, %Y'),
                        open=open_price,
                        high=high_price,
                        low=low_price,
                        close=close_price,
                        volume=volume
                    )
                    price_instance.save()
                logging.info(f"Saved data for date: {date}")

                if date == stop_date:
                    msg = "Reached stop date. Exiting the loop"
                    break
            else:
                logging.warning("Row < 5")
    except Stock.DoesNotExist:
        msg = f"Stock with code '{stock_symbol}' not found."
        logging.error(msg)
    except Exception as e:
        msg = f"An error occurred: {str(e)}"
        logging.error(msg)
    finally:
        driver.quit()  # Close the browser session

    return msg

@app.task
def scraping():
    stock_codes_query = Stock.objects.values_list('code', flat=True)
    stock_codes_list = list(stock_codes_query)

    messages = []  # Store messages for each stock code
    for stock_code in stock_codes_list:
        msg = scrape_stock_data(stock_code)
        messages.append({'stock_code': stock_code, 'msg': msg})

    return {'messages': messages}