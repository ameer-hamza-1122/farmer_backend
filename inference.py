import pickle
import numpy as np
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input  # Change if you used a different backbone
import sys

# --- Load the trained model ---
with open("leaf_disease_model.pkl", "rb") as f:
    model_dict = pickle.load(f)
    model = model_dict['model']  # ✅ Access actual Keras model


# --- Load and preprocess the image ---
def load_image(img_path, target_size=(224, 224)):  # Update target_size based on your training
    img = image.load_img(img_path, target_size=target_size)
    img_array = image.img_to_array(img)
    img_array = preprocess_input(img_array)  # Change if you used a different preprocessing method
    return np.expand_dims(img_array, axis=0)  # Add batch dimension

# --- Inference function ---
def predict_image(img_path):
    img_tensor = load_image(img_path)
    preds = model.predict(img_tensor)
    
    if preds.shape[-1] == 1:
        # Binary classification
        predicted_class = int(preds[0][0] > 0.5)
    else:
        # Multi-class classification
        predicted_class = np.argmax(preds, axis=1)[0]
    
    print(f"Predicted class index: {predicted_class}")
    return predicted_class

# --- Run the script from command line ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inference.py <path_to_image>")
    else:
        img_path = sys.argv[1]
        predict_image(img_path)
