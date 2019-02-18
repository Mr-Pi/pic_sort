import face_recognition
import cv2

try:
    preview_enabled
except NameError:
    preview_enabled = False


def show_preview(enabled):
    preview_enabled = enabled


def detect_faces(path):
    image = face_recognition.load_image_file(path)
    if preview_enabled:
        image_preview = image.copy()

    face_locations = face_recognition.face_locations(image)
    face_encodings = face_recognition.face_encodings(image, face_locations)

    summary = []
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        if preview_enabled:
            cv2.rectangle(image_preview, (left, top), (right, bottom), (0, 0, 255), 2)
            cv2.imshow('preview', image_preview[:,:,::-1])
        summary.append({'top':top, 'right': right, 'bottom': bottom, 'left': left, 'encoding': face_encoding})
    return summary
