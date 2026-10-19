from zk import ZK, const
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd

RUTA_BASE = Path(__file__).resolve().parent
load_dotenv(RUTA_BASE / ".env")


load_dotenv()

ip = os.environ.get("IP")
port = os.environ.get("PORT")
password = os.environ.get("PASSWORD")

fecha_inicio = pd.to_datetime("2026-09-01").date()
fecha_fin = pd.to_datetime("2026-09-30").date()

conn = None
zk = ZK(str(ip), port=int(port),password=str(password) ,timeout=5)
try:
    print ("Connecting to device ...")
    conn = zk.connect()
    print ("Disabling device ...")
    conn.disable_device()
    print (f"Firmware Version: : {conn.get_firmware_version()}")
    
    # print '--- Get User usuarios---'
    #nuevoo
     # Obtener empleados
    print("--- Get Users ---")
    usuarios = conn.get_users()

    # Relacionar los usuarios por su ID
    empleados = {}

    for usuario in usuarios:
        empleados[str(usuario.user_id)] = usuario

    # Obtener registros de asistencia
    print("--- Get Attendance ---")
    asistencias = conn.get_attendance()

    # Obtener nombre del dispositivo
    try:
        dispositivo = conn.get_device_name()
    except Exception:
        dispositivo = "ZKTeco K40"

    datos = []

    for registro in asistencias:
        #Separar fecha y hora
        fecha = registro.timestamp.date()
        hora = registro.timestamp.time()

        if fecha < fecha_inicio or fecha > fecha_fin:continue

        usuario = empleados.get(str(registro.user_id))
        

        if usuario is None:
            usuario = next(
                (u for u in usuarios
                 if u.uid == registro.uid),
                None
            )

        nombre = usuario.name if usuario else "No encontrado"

        # Interpretar el código de marcación e/s
        if registro.punch == 0:
            estado = "Entrada"
        elif registro.punch == 1:
            estado = "Salida"
        else:
            estado = str(registro.punch)

        datos.append({
            "ID": registro.uid,
            "Nombre": nombre,
            "ID usuario": registro.user_id,
            "Fecha": fecha,
            "Hora": hora,
            "Estado": estado,
            "Dispositivo": dispositivo,
            "Tipo de registro": registro.status
        })
    # Crear un solo archivo Excel
    df = pd.DataFrame(datos)

    # Export Excel
    ruta_excel = RUTA_BASE / "asistencia_prueba.xlsx"

    df.to_excel(ruta_excel, index=False, sheet_name="Asistencia"
    )

    #print (f"/n--Asistencia del {fecha_inicio}"
     #      f"A {fecha_fin}--"
      #     )
    #if not df.empty:
     #   print(df.to_string(index=False))
    #else:
     #   print("No hay marcaciones en ese rango de fechas.")
    print("Archivo exportado con exito")
    print(f"\nTotal de marcaciones: {len(df)}")
    print(f"Archivo guardado en: {ruta_excel}")

    conn.enable_device()
except Exception as e:
    print ({e})
finally:
    if conn:
        conn.disconnect()