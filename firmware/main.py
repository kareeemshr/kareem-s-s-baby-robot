from gpiozero import *
import time
import cv2 as cv
from ultralytics import YOLO
from queue import Queue, Empty
import threading
import random
from picamera2 import Picamera2
import board
import busio
import adafruit_vl53l0x
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_vl53l0x.VL53L0X(i2c)
sensor.measurement_timing_budget = 200000
model = YOLO("yolo26n_ncnn_model")
front_left_motor =Motor(forward=22,backward=23)
front_right_motor =Motor(forward=17,backward=18)
back_left_motor = Motor(forward=24 , backward=25)
back_right_motor = Motor(forward=12 , backward=13)
robot = Robot(left=(back_left_motor,front_left_motor),right=(front_right_motor,back_right_motor))
tof_sensor_scl = 3
tof_sensor_sda = 2
picam = Picamera2()
touch_sensor =Button(3)
picam.configure(picam.create_preview_configuration(main={"size":(480,480)}))
picam.start()
time_since_last_pet =0
detection_queue =Queue(maxsize=1)
frame_lock =threading.Lock()
latest_detections=[]


def vision_thread():
    global latest_detections
    while True:
        frame = picam.capture_array()
        small = cv.resize(frame,(320,320))
        results =model(
            small,
            verbose=False,
            imgsz=320,
            classes=[0],
            
            )
        if not detection_queue.full():
            detection_queue.put(results[0])
        
        with frame_lock:
            latest_detections = results[0].boxes.data.tolist()
        time.sleep(0.01)

thread = threading.Thread(target=vision_thread,daemon=True)
thread.start()


try:
    while True:
        dist =sensor.range
        
        try:
            #takes the largest first person it detects 
            results = detection_queue.get_nowait()
            person_boxes = [box for box in results.boxes.data if int(box[5])==0]
        except Empty:
            person_boxes = []
        petted=False
        if touch_sensor.is_pressed:
            petted =True
        if petted and (time.time()-time_since_last_pet>2.0):
            time_since_last_pet = time.time()
            print("uwu being pet(cringe alret!!!)")
            for i in range(4):
                robot.left(0.7)
                time.sleep(0.25)
                robot.right(0.7)
                time.sleep(0.25)
            robot.stop()
        if person_boxes:

            x_center = (person_boxes[0][0]+person_boxes[0][2])/2
            frame_center =160
            if x_center <frame_center -40:
                robot.left(0.4)
                print("left")
            elif x_center > frame_center +40:
                robot.right(0.4)
                print("right")
            else:
                if dist >1000:

                    robot.forward(0.6)
                    print("forward")
                else:
                    robot.stop()
                    print("stopped cus less robot is closer than one meter")
        else:
            if random.random()<0.6:
                robot.forward(0.5)    
            else: 
                robot.right(0.3) if random.random()<0.5 else robot.left(0.3)
            time.sleep(1.5)
        time.sleep(0.05)
except KeyboardInterrupt:
    robot.stop()
    picam.stop()
    print("shutting downn")