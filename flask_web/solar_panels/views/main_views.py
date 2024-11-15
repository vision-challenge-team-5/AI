from flask import Blueprint, render_template, Response, request, jsonify
import torch
from ultralytics import YOLOv10
import cv2
import imutils
import base64
import numpy as np

# YOLOv10 모델 로드 (ultralytics 라이브러리 사용)
model = YOLOv10('./solar_panels/models/best_v2.pt')

# 카테고리 이름 설정
category_names = ['bird_drop', 'cracked', 'dusty', 'panel']

bp = Blueprint('main', __name__, url_prefix='/', template_folder='templates')    # 블루프린트 객체

def process_frame(frame, confidence_threshold=0.3, nms_threshold=0.5):
    frame = imutils.resize(frame, width=350)

    # YOLOv10을 사용하여 프레임 예측
    results = model(frame)

    # 탐지 결과를 저장할 리스트
    detections_list = []

    # 탐지된 객체 가져오기
    boxes = results[0].boxes
    if boxes is None or boxes.shape[0] == 0:
        return frame, detections_list  # 탐지된 객체가 없을 경우

    # 박스 좌표, 신뢰도, 클래스 ID 가져오기
    boxes_data = boxes.data.cpu().numpy()

    # NMS 적용을 위한 데이터 분리
    confidences = boxes_data[:, 4]
    class_ids = boxes_data[:, 5].astype(int)
    bboxes = boxes_data[:, :4]

    # 신뢰도 임계값 적용
    indices = np.where(confidences > confidence_threshold)[0]
    confidences = confidences[indices]
    class_ids = class_ids[indices]
    bboxes = bboxes[indices]

    # NMS 적용
    indices = cv2.dnn.NMSBoxes(
        bboxes.tolist(), confidences.tolist(), confidence_threshold, nms_threshold)

    if len(indices) > 0:
        for i in indices.flatten():
            x1, y1, x2, y2 = bboxes[i].astype(int)
            conf = confidences[i]
            cls = class_ids[i]
            label = category_names[cls]

            # 탐지 결과 저장 (panel 포함)
            detections_list.append({
                'label': label,
                'confidence': float(conf),
                'box': {
                    'x1': int(x1),
                    'y1': int(y1),
                    'x2': int(x2),
                    'y2': int(y2)
                }
            })

            # 'panel' 클래스는 이미지에 표시하지 않음
            if label != 'panel':
                # 박스 그리기
                cv2.rectangle(frame, (x1, y1), (x2, y2),
                              (0, 255, 0), 2)
                # 라벨 및 신뢰도 표시
                cv2.putText(frame, f'{label} {conf * 100:.2f}%',
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX,
                            0.9, (0, 255, 0), 2)

    return frame, detections_list



@bp.route('/')  # 해당 주소 접속 시 함수 호출(데코레이터)
def index():
    return 'Homepage'

@bp.route('/process_image', methods=['POST'])
def process_image():
    try:
        # 요청으로부터 신뢰도 임계값 받아오기 (기본값 0.3)
        confidence_threshold = float(request.form.get('confidence', 0.3))

        # 요청으로부터 NMS 임계값 받아오기 (기본값 0.5)
        nms_threshold = float(request.form.get('nms_threshold', 1))

        # 요청으로부터 이미지 받기
        if 'image' not in request.files:
            return jsonify({'error': '이미지 파일이 제공되지 않았습니다.'}), 400

        file = request.files['image']

        # 파일을 읽어서 OpenCV 이미지로 변환
        img_bytes = file.read()
        npimg = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({'error': '유효하지 않은 이미지 파일입니다.'}), 400

        # 이미지 처리
        processed_frame, detections = process_frame(
            frame,
            confidence_threshold=confidence_threshold,
            nms_threshold=nms_threshold
        )

        # 처리된 이미지를 JPEG로 인코딩하고 Base64로 변환
        _, buffer = cv2.imencode('.jpg', processed_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')

        # 결과 반환 (이미지와 탐지 정보)
        return jsonify({
            'processed_image': frame_base64,
            'detections': detections
        })
    except Exception as e:
        return jsonify({'error': f'서버 오류가 발생하였습니다: {str(e)}'}), 500
