import logging
import os
import tempfile
import uuid
from contextlib import contextmanager

from PIL import Image

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DeepFace = None
    DEEPFACE_AVAILABLE = False

logger = logging.getLogger("face_verification")

MODEL_NAME = "ArcFace"
DETECTOR_BACKEND = "retinaface"
MAX_DISTANCE = 0.58
REQUIRE_ANTISPOOFING = True


@contextmanager
def _temp_jpeg_files(*labels):
    request_id = uuid.uuid4().hex
    temp_dir = tempfile.gettempdir()
    paths = [
        os.path.join(temp_dir, f"{label}_{request_id}.jpg")
        for label in labels
    ]
    try:
        yield paths
    finally:
        for p in paths:
            try:
                if os.path.exists(p):
                    os.remove(p)
            except OSError:
                logger.warning("Vaqtinchalik faylni o'chirib bo'lmadi: %s", p)


def _save_as_rgb_jpeg(source, dest_path):
    with Image.open(source) as image:
        image.load()
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(dest_path, format="JPEG", quality=95)


def verify_face_image(uploaded_file):
    if not DEEPFACE_AVAILABLE:
        logger.error("DeepFace o'rnatilmagan — profil rasmi rad etildi.")
        return False, "Tekshiruv tizimi tayyor emas. Administratorga murojaat qiling."

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    with _temp_jpeg_files("profile_upload") as (temp_path,):
        try:
            _save_as_rgb_jpeg(uploaded_file, temp_path)

            faces = DeepFace.extract_faces(
                img_path=temp_path,
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=True,
                anti_spoofing=REQUIRE_ANTISPOOFING,
            )

            if not faces:
                return False, "Rasmda yuz aniqlanmadi."

            if len(faces) > 1:
                return False, "Rasmda bir nechta yuz bor. Faqat o'zingiz bo'lgan rasm yuboring."

            if REQUIRE_ANTISPOOFING and not faces[0].get("is_real", False):
                return False, "Rasm haqiqiy emas (ekran yoki qog'ozdan olingan)."

            return True, "Yuz muvaffaqiyatli aniqlandi."

        except ValueError:
            return False, "Rasmda yuz topilmadi. Iltimos, aniq rasm yuboring."
        except Exception as e:
            logger.exception("verify_face_image kutilmagan xatolik")
            return False, "Rasmni tekshirishda xatolik yuz berdi. Qayta urinib ko'ring."


def hash_compare(employee, uploaded_file):
    if not DEEPFACE_AVAILABLE:
        logger.error("DeepFace o'rnatilmagan — davomat rad etildi.")
        return False, "Tekshiruv tizimi tayyor emas. Administratorga murojaat qiling."

    if not getattr(employee, "face_image", None) or not employee.face_image.name:
        return False, "Profil rasmi mavjud emas. Avval yuzingizni ro'yxatdan o'tkazing."

    with _temp_jpeg_files(f"base_{employee.id}", f"probe_{employee.id}") as (base_path, probe_path):
        try:
            employee.face_image.seek(0)
            with open(base_path, "wb") as f:
                f.write(employee.face_image.read())
            employee.face_image.seek(0)

            try:
                uploaded_file.seek(0)
            except Exception:
                pass
            _save_as_rgb_jpeg(uploaded_file, probe_path)

            result = DeepFace.verify(
                img1_path=base_path,
                img2_path=probe_path,
                model_name=MODEL_NAME,
                detector_backend=DETECTOR_BACKEND,
                distance_metric="cosine",
                enforce_detection=True,
                anti_spoofing=REQUIRE_ANTISPOOFING,
            )

            if REQUIRE_ANTISPOOFING and not result.get("is_real", False):
                logger.info("Davomat rad etildi (spoofing): employee=%s", employee.id)
                return False, "Qalloblik aniqlandi! Rasm tirik odam emas (ekran yoki qog'oz)."

            distance = result.get("distance")
            if distance is None:
                logger.error("DeepFace natijasida 'distance' yo'q: %s", result)
                return False, "Tekshiruv natijasi noto'g'ri. Qayta urinib ko'ring."

            if distance > MAX_DISTANCE:
                logger.info(
                    "Davomat rad etildi (mos kelmadi): employee=%s distance=%.4f > %.4f",
                    employee.id, distance, MAX_DISTANCE,
                )
                return False, "Yuz mos kelmadi. Rasm xodimning yuziga to'g'ri kelmadi."

            logger.info(
                "Davomat tasdiqlandi: employee=%s distance=%.4f",
                employee.id, distance,
            )
            return True, "Muvaffaqiyatli."

        except ValueError:
            # Yuz topilmadi (profilda yoki yuklangan rasmda)
            return False, "Rasmda yuz aniqlanmadi. Iltimos, aniq rasm yuboring."
        except Exception as e:
            logger.exception("hash_compare kutilmagan xatolik: employee=%s", employee.id)
            # FAIL-CLOSED
            return False, "Tekshiruvda xatolik yuz berdi. Qayta urinib ko'ring."