from zk import ZK, const
from dotenv import load_dotenv
from pathlib import Path
import os
import pandas as pd
from flask import Flask, jsonify
import inspect

RUTA_BASE = Path(__file__).resolve().parent
load_dotenv(RUTA_BASE / ".env")

app = Flask(__name__)

load_dotenv()

ip = os.environ.get("IP")
port = os.environ.get("PORT")
password = os.environ.get("PASSWORD")

fecha_inicio = pd.to_datetime("2026-09-01").date()
fecha_fin = pd.to_datetime("2026-09-03").date()

conn = None
zk = ZK(str(ip), port=int(port), password=str(password), timeout=5)


@app.route("/")
def inicio():
    return "Hola Mundo"


@app.route("/api/prueba")
def prueba():
    return "json", 202


@app.route("/api/usuarios")
def usuarios():
    try:
        print("Connecting to device ...")
        conn = zk.connect()
        print("Disabling device ...")
        conn.disable_device()
        print(f"Firmware Version: : {conn.get_firmware_version()}")
        print("Tamaño del paquete de usuario:", conn.user_packet_size)

        print("--- Get Users ---")
        usuarios = conn.get_users()

        resultado = []

        for usuario in usuarios:
            resultado.append(
                {
                    "uid": usuario.uid,
                    "user_id": usuario.user_id,
                    "nombre": usuario.name,
                    "privilegio": usuario.privilege,
                    "password": usuario.password,
                    "tarjeta": usuario.card,
                }
            )

        return jsonify({"usuarios": resultado}), 200

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if conn:
            try:
                conn.enable_device()
                conn.disconnect()
            except:
                pass


@app.route("/api/asistencias")
def asistencias():

    try:
        print("Connecting to device ...")
        conn = zk.connect()
        print("Disabling device ...")
        conn.disable_device()
        print(f"Firmware Version: {conn.get_firmware_version()}")

        print("--- Get Asistencia ---")
        registros_asistencia = conn.get_attendance()
        dispositivo = conn.get_device_name()

        resultado = []

        for asistencia in registros_asistencia:
            # Validar que el timestamp exista
            if not asistencia.timestamp:
                continue

            # Convertir de forma segura sin importar si es string o datetime
            dt = pd.to_datetime(asistencia.timestamp)
            fecha = dt.date()
            hora = dt.time()

            if fecha < fecha_inicio or fecha > fecha_fin:
                continue

            if asistencia.punch == 0:
                estado = "Entrada"
            elif asistencia.punch == 1:
                estado = "Salida"
            else:
                estado = str(asistencia.punch)

            resultado.append(
                {
                    "ID usuario": asistencia.user_id,
                    "Fecha": str(fecha),
                    "Hora": str(hora),
                    "Dispositivo": dispositivo,
                    "Estado": estado,
                    "Tipo de registro": asistencia.status,
                }
            )

        return jsonify({"asistencias": resultado}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            try:
                conn.enable_device()
                conn.disconnect()
            except:
                pass


@app.route("/api/plantilla")
def plantilla():
    try:
        print("Connecting to device ...")
        conn = zk.connect()

        print("=== FIRMA DE LAS FUNCIONES ===")

        for nombre in [
            "get_templates",
            "get_user_template",
            "save_user_template",
            "set_user",
        ]:
            funcion = getattr(conn, nombre, None)

            if funcion:
                try:
                    print(nombre, inspect.signature(funcion))
                    print(inspect.getdoc(funcion))
                except (TypeError, ValueError):
                    print(nombre, "No se pudo inspeccionar")

        print("=== FUNCIONES DE USUARIOS Y PLANTILLAS ===")

        for nombre in dir(conn):
            if any(
                palabra in nombre.lower() for palabra in ["user", "template", "finger"]
            ):
                print(nombre)

        print("Disabling device ...")
        conn.disable_device()
        print(f"Firmware Version: : {conn.get_firmware_version()}")

        print("--- Get Users ---")
        plantilla = conn.get_templates()

        resultado = []

        for huella in plantilla:
            resultado.append(
                {
                    "uid": huella.uid,
                    "Dedo": huella.fid,
                    "Valida": huella.valid,
                    "Tamano": huella.size,
                }
            )

        return jsonify({"plantilla": resultado}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            try:
                conn.enable_device()
                conn.disconnect()
            except:
                pass


@app.route("/api/diagnostico_plantilla/<int:uid>")
def diagnostico_plantilla(uid):
    conn = None

    try:
        print("Conectando al reloj...")
        conn = zk.connect()

        # 1. Consultar los usuarios registrados
        print("Consultando usuarios...")
        usuarios = conn.get_users() or []

        usuario = next((u for u in usuarios if u.uid == uid), None)

        if usuario is None:
            return (
                jsonify(
                    {"error": "No se encontró el UID indicado", "uid_consultado": uid}
                ),
                404,
            )

        print(f"Usuario encontrado: {usuario.name}")
        print(f"UID interno: {usuario.uid}")
        print(f"ID de usuario: {usuario.user_id}")

        # 2. Consultar las plantillas de este usuario por dedo
        print("=== ESTRUCTURA DEL USUARIO ===")
        print("Clase:", type(usuario).__name__)
        print("Atributos:", list(vars(usuario).keys()))

        print("=== ESTRUCTURA DE LAS PLANTILLAS ===")

        for temp_id in [3, 6]:
            try:
                huella = conn.get_user_template(
                    uid=usuario.uid, temp_id=temp_id, user_id=usuario.user_id
                )

                if huella is None:
                    print(f"temp_id={temp_id}: sin resultado")
                    continue

                # No imprimir el contenido biométrico
                print(f"temp_id={temp_id}")
                print("Clase:", type(huella).__name__)
                print("Atributos:", list(vars(huella).keys()))

                for atributo, valor in vars(huella).items():
                    if atributo.lower() in ("template", "data", "template_data"):
                        print(
                            f"{atributo}: tipo={type(valor).__name__}, "
                            f"longitud={len(valor) if valor is not None else 0}"
                        )
                    elif atributo in ("uid", "fid", "valid", "size"):
                        print(f"{atributo}: {valor}")

            except Exception as e:
                print(f"Error en temp_id={temp_id}: {e}")

        # 2.1 Consultar las plantillas por cada índice de dedo
        print("=== CONSULTA INDIVIDUAL POR DEDO ===")

        resultado_por_dedo = []

        for temp_id in range(10):
            try:
                respuesta = conn.get_user_template(
                    uid=usuario.uid, temp_id=temp_id, user_id=usuario.user_id
                )

                if respuesta is None:
                    dedos = []
                elif isinstance(respuesta, list):
                    dedos = respuesta
                else:
                    # La biblioteca también puede devolver un Finger individual
                    dedos = [respuesta]

                print(f"temp_id={temp_id}: {len(dedos)} plantilla(s)")

                for huella in dedos:
                    resultado_por_dedo.append(
                        {
                            "temp_id_consultado": temp_id,
                            "uid": getattr(huella, "uid", None),
                            "fid": getattr(huella, "fid", None),
                            "valid": getattr(huella, "valid", None),
                            "size": getattr(huella, "size", None),
                            "tipo_objeto": type(huella).__name__,
                        }
                    )

            except Exception as e:
                print(f"Error consultando temp_id={temp_id}: {e}")

        # 3. Consultar todas las plantillas del reloj
        print("Consultando todas las plantillas...")
        todas_plantillas = conn.get_templates() or []

        resultado_general = []

        for huella in todas_plantillas:
            resultado_general.append(
                {
                    "uid": getattr(huella, "uid", None),
                    "fid": getattr(huella, "fid", None),
                    "valid": getattr(huella, "valid", None),
                    "size": getattr(huella, "size", None),
                }
            )

        # 4. Buscar plantillas con el UID interno consultado
        plantillas_mismo_uid = [
            huella for huella in resultado_general if huella["uid"] == usuario.uid
        ]

        print("Plantillas individuales:", len(resultado_por_dedo))
        print("Total de plantillas del reloj:", len(resultado_general))
        print("Plantillas asociadas al UID consultado:", len(plantillas_mismo_uid))

        return (
            jsonify(
                {
                    "usuario": {
                        "uid": usuario.uid,
                        "user_id": usuario.user_id,
                        "nombre": usuario.name,
                    },
                    "consulta_individual": {
                        "consulta_por_dedo": resultado_por_dedo,
                    },
                    "consulta_general": {
                        "cantidad_total": len(resultado_general),
                        "cantidad_mismo_uid": len(plantillas_mismo_uid),
                        "plantillas_mismo_uid": plantillas_mismo_uid,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        print(f"Error durante el diagnóstico: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        if conn:
            try:
                conn.disconnect()
                print("Conexión cerrada.")
            except Exception as e:
                print(f"Error al cerrar conexión: {e}")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1435, debug=True)
