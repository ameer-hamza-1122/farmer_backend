from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time 
import json
import os
def get_details(urls):
    for url in urls:
        driver = webdriver.Chrome()
        driver.get(url)
        name=''
        image=''
        rating=''
        location=''
        phone_number=''
        latitude=''
        try:
            raw_name=driver.find_element(By.XPATH,"//h1[@class='DUwDvf lfPIob']")
            if raw_name.text:
                name=raw_name.text
        except Exception as e:
            print(e)   
        try:
            raw_img=driver.find_element(By.XPATH,"//button[@class='aoRNLd kn2E5e NMjTrf lvtCsd '] //img")
            if raw_img.get_attribute("src"):
                image=raw_img.get_attribute("src")
        except Exception as e:
            print (e)        
        try:
            raw_rating=driver.find_element(By.XPATH,"//span[@class='ceNzKf']")
            if raw_rating:
                rating=raw_rating.get_attribute("aria-label")
        except Exception as e:
            print("rating does not exists.")

        try:
            raw_data=driver.find_elements(By.XPATH,"//div[@class='Io6YTe fontBodyMedium kR99db fdkmkc ']")
            try:
                raw_location=raw_data[0].get_attribute("outerHTML")
                raw_location=BeautifulSoup(raw_location,'html.parser')
                location=raw_location.text
            except Exception as e:
                print("location does not exists.") 
            try:
                raw_number=raw_data[1].get_attribute("outerHTML")
                raw_number=BeautifulSoup(raw_number,'html.parser')
                phone_number=raw_number.text
            except Exception as e:
                print("number does not exists.") 
            try:
                raw_latitude=raw_data[2].get_attribute("outerHTML")
                raw_latitude=BeautifulSoup(raw_latitude,'html.parser')
                latitude=raw_latitude.text
            except Exception as e:
                print("number does not exists.")       
        except Exception as e:
            print("location ,number ,latitude does not found.")   
        end_data={
        'Url':url,
        'Name':name,
        'Image':image,
        'Rating':rating,
        'Location':location,
        'Phone number':phone_number,
        'Latitude':latitude
        }   
        driver.close()
        json_file = 'details.json'

        if os.path.exists(json_file) and os.path.getsize(json_file) > 0:
            try:
                with open(json_file, 'r', encoding='utf-8') as file:
                    data = json.load(file)
            except json.JSONDecodeError:
                print("Warning: Malformed JSON. Starting with empty list.")
                data = []
        else:
            data = []
        data.append(end_data)
        with open(json_file, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

    
   
if __name__=='__main__':
   with open ("cities_urls.json","r") as f:
      urls=json.load(f)
   get_details(urls)   