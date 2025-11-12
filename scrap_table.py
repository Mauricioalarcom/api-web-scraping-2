from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import boto3
import uuid
import time
import json

def lambda_handler(event, context):
    # Configurar opciones de Selenium para usar el navegador headless (sin UI)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    # Ruta al ejecutable de Chrome y Chromedriver (ajústalo según tu entorno)
    service = Service('/path/to/chromedriver')  # Cambia la ruta de chromedriver si es necesario
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # URL de la página web que contiene los sismos
    url = "https://ultimosismo.igp.gob.pe/ultimo-sismo/sismos-reportados"

    # Acceder a la página web
    driver.get(url)

    # Esperar que la página cargue completamente (ajusta si es necesario)
    time.sleep(5)

    # Obtener el HTML renderizado después de que JavaScript haya cargado la página
    html = driver.page_source

    # Parsear el HTML con BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Intentar encontrar la tabla que contiene los sismos (ajusta el selector si es necesario)
    table = soup.find('table', {'class': 'tabla'})  # Cambia según el elemento correcto de la página

    if not table:
        driver.quit()
        return {
            'statusCode': 404,
            'body': 'No se encontró la tabla de sismos en la página web'
        }

    # Extraer los encabezados de la tabla (si es necesario)
    headers = [header.text.strip() for header in table.find_all('th')]

    # Extraer las filas de la tabla (limitar a los 10 primeros sismos)
    rows = []
    for row in table.find_all('tr')[1:11]:  # Limitar a los primeros 10 sismos
        cells = row.find_all('td')
        if len(cells) > 0:
            sismo = {
                'fecha': cells[0].text.strip(),
                'hora': cells[1].text.strip(),
                'latitud': cells[2].text.strip(),
                'longitud': cells[3].text.strip(),
                'profundidad': cells[4].text.strip(),
                'magnitud': cells[5].text.strip(),
                'lugar': cells[6].text.strip(),
            }
            rows.append(sismo)

    # Guardar los datos en DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('SismosReportados')

    # Eliminar todos los elementos de la tabla antes de agregar los nuevos
    scan = table.scan()
    with table.batch_writer() as batch:
        for each in scan['Items']:
            batch.delete_item(Key={'id': each['id']})

    # Insertar los nuevos datos en DynamoDB
    for i, sismo in enumerate(rows):
        sismo['id'] = str(uuid.uuid4())  # Generar un ID único para cada entrada
        table.put_item(Item=sismo)

    # Cerrar el navegador de Selenium
    driver.quit()

    # Retornar el resultado como JSON
    return {
        'statusCode': 200,
        'body': json.dumps(rows)
    }
