import argparse
import time
from pathlib import Path

import cv2
import torch
from numpy import random

from models.experimental import attempt_load
from utils.datasets import LoadStreams, LoadImages
from utils.general import check_img_size, check_requirements, check_imshow, non_max_suppression, apply_classifier, \
    scale_coords, xyxy2xywh, strip_optimizer, set_logging, increment_path
from utils.plots import plot_one_box
from utils.torch_utils import select_device, load_classifier, time_synchronized
import os

def detect(file_name):

    agnostic_nms=False
    augment=False
    classes=None
    conf_thres=0.25
    device=''
    exist_ok=True
    imgsz=640
    iou_thres=0.45
    name='result_img'
    nosave=False
    project='static'
    save_conf=False
    save_txt=True
    source = 'uploads/' + file_name
    update=False
    view_img=True
    weights='best.pt'
    save_img = True

    # Directories
    #print('-->detect')
    save_dir = Path(increment_path(Path(project) / name, exist_ok=True))  # increment run


    # Initialize
    #print('-->Initialize')
    set_logging()
    device = select_device(device)
    half = device.type != 'cpu'  # half precision only supported on CUDA

    # Load model
    #print('-->Load model')
    model = attempt_load(weights, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    imgsz = check_img_size(imgsz, s=stride)  # check img_size
    if half:
        model.half()  # to FP16

    classify = False


    # Set Dataloader
    print('-->Set Dataloader')
    vid_path, vid_writer = None, None


    #print('-->3 source:',source)
    #print('-->3 file_name:',file_name)

    #print('-->4 source:',source)


    dataset = LoadImages(source, img_size=imgsz, stride=stride)

    # Get names and colors
    print('-->Get names and colors')
    names = model.module.names if hasattr(model, 'module') else model.names
    colors = [[random.randint(0, 255) for _ in range(3)] for _ in names]

    # Run inference
    print('-->Run inference')
    print('device type :', device.type)
    if device.type != 'cpu':
        model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    t0 = time.time()

    labels  = []

    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        img = img.half() if half else img.float()  # uint8 to fp16/32
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if img.ndimension() == 3:
            img = img.unsqueeze(0)

        # Inference
        print('-->Inference')
        t1 = time_synchronized()
        pred = model(img, augment=augment)[0]

        # Apply NMS
        print('-->Apply NMS')
        pred = non_max_suppression(pred, conf_thres, iou_thres, classes=classes, agnostic=agnostic_nms)
        t2 = time_synchronized()

        # Apply Classifier
        print('-->Apply Classifier')
        if classify:
            pred = apply_classifier(pred, modelc, img, im0s)

        # Process detections
        print('-->Process detections')


        for i, det in enumerate(pred):  # detections per image
            p, s, im0, frame = path, '', im0s, getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path
            save_path = str(save_dir / p.name)  # img.jpg
            txt_path = str(save_dir /  p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # img.txt
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh

            # ysc  20210420  delete old file , add labe list
            if os.path.isfile(txt_path + '.txt'):
                os.remove(txt_path + '.txt')

            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                print('-->Print results')
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string


                # Write results
                print('-->Write results')
                for *xyxy, conf, cls in reversed(det):
                    if save_txt:  # Write to file
                        label = f'{names[int(cls)]} {conf:.2f}' # detected label name
                        with open(txt_path + '.txt', 'a') as f:
                            f.write(label +  '\n')

                    if save_img or view_img:  # Add bbox to image
                        label = f'{names[int(cls)]}-{conf:.2f}'
                        plot_one_box(xyxy, im0, label=label, color=colors[int(cls)], line_thickness=3)

                        print('-->label :' ,label)
                    labels.append(label)

            # Print time (inference + NMS)
            print(f'{s}Done. ({t2 - t1:.3f}s)')


            # Save results (image with detections)
            print('-->Save results (image with detections)')
            if save_img:
                cv2.imwrite(save_path, im0)

    print('labels=',labels)

    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
        print(f"Results saved to {save_dir}{s}")

    print(f'Done. ({time.time() - t0:.3f}s)')

    return labels




if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='best.pt', help='model.pt path(s)')
    parser.add_argument('--source', type=str, default='uploads', help='source')  # file/folder, 0 for webcam
    parser.add_argument('--img-size', type=int, default=640, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='object confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='IOU threshold for NMS')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--view-img', action='store_true', help='display results')
    parser.add_argument('--save-txt', default='-txt', help='save results to *.txt')
    parser.add_argument('--save-conf', action='store_true', help='save confidences in --save-txt labels')
    parser.add_argument('--nosave', action='store_true', help='do not save images/videos')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--update', action='store_true', help='update all models')
    parser.add_argument('--project', default='static', help='save results to project/name')
    parser.add_argument('--name', default='result_img', help='save results to project/name')
    parser.add_argument('--exist-ok', default=True, help='existing project/name ok, do not increment')
    opt = parser.parse_args()
    print(opt)
    #check_requirements(exclude=('pycocotools', 'thop'))
    file_name = 'mask01.jpg'
    with torch.no_grad():
        if opt.update:  # update all models (to fix SourceChangeWarning)
            for weights in ['yolov5s.pt', 'yolov5m.pt', 'yolov5l.pt', 'yolov5x.pt']:
                detect(file_name)
                strip_optimizer(weights)
        else:
            detect(file_name)
