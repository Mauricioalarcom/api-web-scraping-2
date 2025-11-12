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
    # Configurar opciones de Selenium para usar el Chrome instalado en la máquina virtual
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    # Definir las rutas para el chromedriver y el binario de chromium
    chrome_options.binary_location = '/usr/bin/chromium-browser'  # Cambia la ruta si es necesario
    service = Service(executable_path='/usr/bin/chromedriver')  # Cambia la ruta si es necesario
    
    # Iniciar Selenium con el Chrome headless y Chromedriver instalado
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # URL de la página web que contiene los sismos
    url = "https://ultimosismo.igp.gob.pe/ultimo-sismo/sismos-reportados"

    # Acceder a la página
    driver.get(url)

    # Esperar un momento para que la página cargue
    time.sleep(5)

    # Obtener el HTML renderizado
    html = driver.page_source

    # Parsear el contenido HTML con BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # Intentar encontrar la tabla que contiene los sismos (ajusta el selector si es necesario)
    table = soup.find('table', class_='tabla')  # Cambia según el elemento correcto

    if not table:
        driver.quit()
        return {
            'statusCode': 404,
            'body': 'No se encontró la tabla de sismos en la página web'
        }

    # Extraer los encabezados de la tabla
    headers = [header.text.strip() for header in table.find_all('th')]

    # Extraer las filas de la tabla
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

    # Insertar los nuevos datos
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
