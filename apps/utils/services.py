import math
import os
import tempfile

from PIL import Image

try:
    from deepface import DeepFace

    DEEPFACE_AVAILABLE = True
except ImportError:
    DeepFace = None
    DEEPFACE_AVAILABLE = False


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def hash_compare(employee, uploaded_file):
    if not DEEPFACE_AVAILABLE:
        return True, "DeepFace o'rnatilmaganligi sababli tekshiruv o'tkazib yuborildi."

    temp_base_path = ""
    temp_path = ""
    try:
        if not employee.face_image or not employee.face_image.name:
            return False, "Profil rasmi mavjud emas"

        temp_dir = tempfile.gettempdir()

        temp_base_path = os.path.join(temp_dir, f"base_face_{employee.id}.jpg")
        with open(temp_base_path, "wb") as f:
            f.write(employee.face_image.read())
            employee.face_image.seek(0)

        temp_path = os.path.join(temp_dir, "temp_face_attendance.jpg")

        image = Image.open(uploaded_file)
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(temp_path)

        result = DeepFace.verify(
            img1_path=temp_base_path,
            img2_path=temp_path,
            model_name="ArcFace",
            detector_backend="retinaface",
            enforce_detection=True,
            anti_spoofing=True,
        )

        if os.path.exists(temp_path):
            os.remove(temp_path)
        if temp_base_path and os.path.exists(temp_base_path):
            os.remove(temp_base_path)

        if not result.get("verified", False):
            return (
                False,
                "Yuzni tekshirish amalga oshmadi. Rasm xodimning yuziga mos kelmadi.",
            )

        if not result.get("is_real", True):
            return (
                False,
                "Qalloblik aniqlandi! Rasm tirik odam emas (ekran yoki qog'ozdan olingan).",
            )

        return True, "Muvaffaqiyatli"

    except ValueError as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if temp_base_path and os.path.exists(temp_base_path):
            os.remove(temp_base_path)
        return False, f"Rasmda yuz aniqlanmadi. Xato: {str(e)}"
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if temp_base_path and os.path.exists(temp_base_path):
            os.remove(temp_base_path)
        print(f"DeepFace kutilmagan xatolik: {e}")
        return False, f"Tizim xatoligi: {e}"


def verify_face_image(uploaded_file):
    if not DEEPFACE_AVAILABLE:
        return True, "DeepFace o'rnatilmaganligi sababli tekshiruv o'tkazib yuborildi."

    temp_path = ""
    try:
        uploaded_file.seek(0)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "temp_profile_upload.jpg")

        image = Image.open(uploaded_file)
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(temp_path)

        faces = DeepFace.extract_faces(
            img_path=temp_path,
            detector_backend="retinaface",
            enforce_detection=True,
            anti_spoofing=True,
        )

        if os.path.exists(temp_path):
            os.remove(temp_path)

        if not faces:
            return False, "Rasmda yuz aniqlanmadi"

        if not faces[0].get("is_real", True):
            return False, "Rasm haqiqiy emas!"

        return True, "Yuz muvaffaqiyatli aniqlandi"

    except ValueError as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"Rasmda yuz topilmadi! Xato: {str(e)}"
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return False, f"Xatolik: {str(e)}"
