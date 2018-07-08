from keras.models import load_model
from gloves import Gloves
from config import process_config
import numpy as np
import os
import time
import pickle
from app_global import *
import cv2
import controllers

class ModeController:
    def __init__(self, configuration_file_path, gloves_name = None):
        """

        :param model_path: path to the static gestures model
        :param configuration_file_path: path to the configuration file to load
        :param glove_path: path to a glove if a pretrained glove is selected
        """

        self.configuration_file = process_config(configuration_file_path)# load the configuration file
        #static_model path
        #model_path = self.configuration_file["static_model_path"]
        model_path = eval( self.configuration_file["static_model_path"] )
        print("static model path:",model_path)

        self.static_model = load_model(model_path)

        self.mouse_controller = controllers.MouseController(self.configuration_file)
        self.keyboard_controller = controllers.KeyboardController(self.configuration_file)
        self.dynamic_controller = controllers.DynamicController(self.configuration_file)

        #add a new glove
        if gloves_name is None:
            file_name = time.strftime("%Y%m%d-%H%M%S")
            self.gloves = Gloves()
            save_path = os.path.join(os.getcwd(), 'Gloves', file_name + '.txt')
            gloves_image = self.gloves.train()

            #pickle.dump(self.gloves, save_path)
            with open(save_path, 'wb') as handle:
                pickle.dump(self.gloves, handle, protocol=pickle.HIGHEST_PROTOCOL)
            image_path = os.path.join(os.getcwd(), 'Gloves', file_name + '.jpg')
            cv2.imwrite(image_path, gloves_image)
        #load a saved glove
        else:
            #self.gloves = pickle.load(os.path.join(os.getcwd(), 'Gloves', gloves_name))
            glove_path = os.path.join(os.getcwd(), "Gloves", gloves_name + ".txt")
            with open(glove_path, 'rb') as handle:
                self.gloves = pickle.load(handle)

        self.current_mode = MODE.KEYBOARD
        self.start()


    def start(self):
        camera = cv2.VideoCapture(0)
        while True:
            if self.current_mode == MODE.DYNAMIC: # Capture 31 frames for classification
                #TODO: wait for t periods, and beep
                centers = []
                for i in range(31):
                    ret_val, image = camera.read()
                    preprocessed_image, _ = self.gloves.preprocess_image(image)
                    center = self.gloves.get_hand_center(preprocessed_image)
                    centers.append(center)
                    action = self.dynamic_controller.take_action(centers)
                    eval(action)

                self.current_mode = MODE.KEYBOARD

            else: # predict the static gesture
                ret_val, image = camera.read()
                preprocessed_image, keras_image = self.gloves.preprocess_image(image)

                prediction = self.predict(keras_image)
                next_mode = self.current_mode

                if self.current_mode == MODE.KEYBOARD:
                    (next_mode, action) = self.mouse_controller.take_action(prediction)
                elif self.current_mode == MODE.MOUSE:
                    (next_mode, action) = self.keyboard_controller.take_action(prediction)
                elif self.current_mode == MODE.DYNAMIC:
                    (next_mode, action) = self.dynamic_controller.take_action(prediction)

                eval(action)
                self.current_mode = next_mode

    def predict(self, image):
        prediction = self.static_model.predict(image)[0]
        prediction = np.array(prediction).argmax()
        return prediction


if __name__ == "__main__":
    path = os.path.join(os.getcwd(), 'config_file.json')
    #print(path)
    controller = ModeController(path)