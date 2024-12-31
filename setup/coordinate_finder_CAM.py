import cv2

coordinate_list = []

def find_pixel():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("failed to open camera")
        return
    
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("failed to capture image")
        return
    
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    min_val, max_val, nim_pos, max_pos = cv2.minMaxLoc(gray_frame)
    
    coordinate_list.append(list(max_pos))
    print(f"brightest pixel found at {max_pos}")

while True:
    if input("press enter to find another pixel, or E then enter to exit.").lower() == 'e':
        print(coordinate_list)
        min_x = 99999
        min_y = 99999
        for coordinate in coordinate_list:
            if coordinate[0] < min_y: min_y = coordinate[0]
            if coordinate[1] < min_x: min_x = coordinate[1]
        for index, coordinate in enumerate(coordinate_list):
            coordinate_list[index] = [coordinate[1]-min_x, coordinate[0]-min_y]
        print(coordinate_list)
        break
    else:
        find_pixel()
        print(coordinate_list)
