import requests
from bs4 import BeautifulSoup
import boto3
import uuid
import json

def lambda_handler(event, context):
    # URL de la página web que contiene los últimos sismos
    url = "https://ultimosismo.igp.gob.pe/ultimo-sismo/sismos-reportados"

    # Realizar la solicitud HTTP a la página web
    response = requests.get(url)
    if response.status_code != 200:
        return {
            'statusCode': response.status_code,
            'body': 'Error al acceder a la página web'
        }

    # Parsear el contenido HTML de la página web
    soup = BeautifulSoup(response.content, 'html.parser')

    # Encontrar la tabla en el HTML
    table = soup.find('table', class_='tabla_sismos')
    if not table:
        return {
            'statusCode': 404,
            'body': 'No se encontró la tabla de sismos en la página web'
        }

    # Extraer los encabezados de la tabla (si existen)
    headers = [header.text.strip() for header in table.find_all('th')]

    # Extraer las filas de la tabla (los últimos 10 sismos)
    rows = []
    for row in table.find_all('tr')[1:11]:  # Tomar solo los primeros 10 sismos
        cells = row.find_all('td')
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

    # Retornar el resultado como JSON
    return {
        'statusCode': 200,
        'body': json.dumps(rows)
    }
