from langchain_google_genai import ChatGoogleGenerativeAI
from google.api_core.exceptions import ResourceExhausted
import time
from datetime import datetime as dt
import yaml
import pprint
import os
import sys

class mitades():
    def __init__(self, limite_max_rango:int) -> None:
        self.opciones = [i for i in range(1, limite_max_rango+1)]
        self.ultma_seleccion = None
    
    def seleccionar_numero(self):
        self.ultma_seleccion = self.opciones[(len(self.opciones)//2)-1]
        return self.ultma_seleccion
    
    def eliminar_opciones(self, indicacion:str):
        if indicacion == "El número secreto es mayor.\n":
            self.opciones = self.opciones[len(self.opciones)//2:]
        elif indicacion == "El número secreto es menor.\n":
            self.opciones = self.opciones[:len(self.opciones)//2]

class gemini():
    def __init__(self,
                 model:str="gemini-1.5-flash",
                 limite_max_rango = 0,
                 now = dt.now()
                 ) -> None:
        
        self.model = model
        self.limite_max_rango = limite_max_rango
        self.respuestas = []
        self.usage_metadata = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "requests": 0,
            "timer": now
        }

        # Cargar API key a variable de entorno
        with open("agente/env.yml", "r") as file:
            os.environ["GOOGGLE_API_KEY"] = yaml.safe_load(file)["GOOGLE_API_KEY"]

        self.llm = ChatGoogleGenerativeAI(
            model=self.model,
            api_key=os.environ["GOOGGLE_API_KEY"],
            temperature=0,
            verbose=True
            )
    
    def limit_minute_quota(self):
        minute_limit = 12
        requests_per_minute = self.usage_metadata["requests"] / ((dt.now() - self.usage_metadata["timer"]).seconds/60)
        if requests_per_minute >= minute_limit:
            return True
        else:
            return False
            
    def agregar_respuesta(self, respuesta:tuple):
        numero, pista = respuesta
        self.respuestas.append(f"{numero}:{pista}")
        

    def seleccionar_numero(self) -> str:

        # Mensaje para primer intento
        if len(self.respuestas) == 0:
            system_msg =(
                "system",
                f"Estamos jugando a que adivines un numero secreto entre el 1 y el {self.limite_max_rango}.\
                Tras cada intento de acierto te diré si el número secreto es mayor o menor a tu número.\
                Es tu primer intento."
            )
        
        # Mensaje para intentos posteriores
        else:
            system_msg = (
                "system",
                f"""Estamos jugando a que adivines un numero secreto entre el 1 y el {self.limite_max_rango}.
                Tras cada intento de acierto te diré si el número secreto es mayor o menor a tu número.
                Te voy a decir que numeros has usado de momento con el formato 'numero:respuesta'.\n
                {','.join(self.respuestas)}\n\
                """
            )

        human_msg = (
            "human",
            "Responde solo caracterers numéricos ¿Cual es el número secreto?"
        )

        mensaje = [system_msg,human_msg]
        
        retry = True

        while retry == True:

            if self.limit_minute_quota():
                    print(f"Se ha excedido el límite de quota por minuto de la API, esperando 10 segundos para reintentar")
                    pprint.pprint(self.usage_metadata)
                    time.sleep(10)
            elif self.usage_metadata["requests"] >= 1500 and (dt.now() - self.usage_metadata["time"]).seconds / 3600 <= 24:
                print(f"Se ha excedido el límite de quota diario de la API, finalizando el proceso")
                pprint.pprint(self.usage_metadata)
                sys.exit()
            else:

                try:
                    respuesta = self.llm.invoke(mensaje)

                except ResourceExhausted:
                    print("Se ha excedido el límite de uso de la API, esperando 15 segundos para reintentar")
                    time.sleep(15)

                else:
                    retry = False
                    self.usage_metadata["requests"] += 1

        # Contabilizar uso de la API
        usage = respuesta.usage_metadata
        for key, value in usage.items():
            self.usage_metadata[key] += value
        
        # Procesar respuesta en caso de que no entregue un número.
        try:
            respuesta = int(respuesta.content.strip())
        except ValueError:
            respuesta = respuesta.content.strip().split(" ")[-1]
            if respuesta[-1] == ".":
                respuesta = int(respuesta[:-1])
            else:
                respuesta = int(respuesta)

        return respuesta

if __name__ == "__main__":
    agente = gemini()
    for i in range(18):
        print(agente.seleccionar_numero())
