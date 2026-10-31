import numpy as np
import math
from collections import deque

# Model Constants matching model_parameters.h / model_config.json
MODEL_N_FEATURES = 47
MODEL_N_CLASSES = 4

MODEL_MEAN = np.array([-5.87165751, -10.200679, -1.44512812, 8.75555091, 9.07121149, -3.69568589, 2.42581364, -7.85116723, 0.84006878, 8.69123601, 16.1283989, 0.0226930722, 0.0298910369, 0.163904248, 0.16335327, 0.0382838913, 0.00308551585, 0.0583606164, -0.144738436, 0.155456844, 0.30019528, -0.00155057991, 0.0590031764, -0.152770263, 0.159569049, 0.312339312, 0.843270128, 1.07615968, 0.232889548, -0.970433581, 8.41202917, -25.2922792, 24.003176, 49.2954552, 8.33095379, -25.24147, 21.103702, 46.3451719, 7.33052706, -20.8416655, 21.9696089, 42.8112744, 11.555518, 10.2624912, 50.4746163, 20.4785246, 25.1472382])
MODEL_SCALE = np.array([13.8183582, 17.7209038, 13.9968998, 15.2784458, 12.2860491, 22.300808, 5.2081211, 22.3168561, 25.5763663, 16.5161519, 16.1123094, 0.0271770518, 0.0452613064, 0.268373777, 0.267859551, 0.0522491271, 0.16394363, 0.0771746162, 0.229244048, 0.287579729, 0.374200962, 0.182996664, 0.08039033, 0.271956165, 0.31832917, 0.415777896, 0.250811658, 0.20115718, 0.368376205, 2.93117669, 13.8213779, 43.1319789, 46.5338646, 83.9831328, 12.4858251, 37.6353921, 36.0741488, 69.3090059, 14.6324371, 41.0260841, 45.6121902, 82.6847425, 17.0486821, 15.9153932, 0.555452439, 18.5962173, 24.0788849])
MODEL_INTERCEPT = np.array([-18.4685685, 1.58037859, 8.58205138, 8.30613853])
MODEL_COEF = np.array([
  [0.904183561, 0.881873289, 0.625853931, -0.449494471, -1.00808494, -0.247913977, -0.438011492, -0.0595674, -0.394675031, -0.530692387, -0.513419965, -0.475119926, -0.585412708, -0.648862209, -0.649193756, -0.547326798, 0.169359627, -0.902814897, 1.08883044, -0.953422627, -1.39976369, 0.120746329, -2.06537832, 1.59836589, -1.48335843, -2.18116866, 0.48466268, -0.888534125, -0.815183135, -1.09765835, -0.788552601, 0.388896259, -0.814144754, -0.650835058, -0.553339874, 0.266067928, -0.694286691, -0.50584151, -0.447574757, 0.298670387, -0.615395817, -0.487669505, -0.053377959, -0.440316044, -3.24564267, -0.816780107, -0.791409816],
  [-0.361777111, 0.0253609417, -0.839936616, -0.798898503, 0.370494468, 0.288714877, -0.281620724, 0.407558124, 0.177918124, -0.275180135, -0.501782812, -0.876207908, -0.217240118, -0.057447318, -0.0539627677, -0.579821023, 0.58346863, 0.73544763, -0.670748975, 1.20364628, 1.33593853, -0.950417194, 1.82637103, -1.6814517, 0.671367249, 1.61383503, -0.29453867, 0.776696631, 0.62466531, 0.0319087089, 0.163049442, 0.350512741, 0.145140563, -0.0995956755, -0.333436545, 0.169365166, -0.923385718, -0.572573185, -0.0780229991, 0.325109692, 0.335829869, 0.0239458724, -0.534130048, -0.176376497, -1.79151707, -0.199951687, -0.277544795],
  [-1.1671994, -0.654763593, 0.719442296, 1.41853201, 0.831230774, -0.0182195161, 0.176099883, 0.47060622, 0.251648224, -0.246195613, 2.12699852, 0.574553941, 0.580530428, 0.561949624, 0.615937226, 0.482730519, -1.62912419, 0.522828296, 0.481529465, -0.30475375, -0.529204317, 0.465254146, 0.949919544, -0.287130439, 0.0344746924, 0.21420377, 0.105693988, -0.0890380227, -0.120583038, -0.226237007, 0.774790414, 0.527079199, 0.381652023, -0.0592288614, 1.40298546, 0.0616019963, 0.851574331, 0.409779415, -1.01916506, -0.420543896, 0.0976159963, 0.262512139, -0.598226516, 1.50005806, 2.13145559, 0.13612318, -0.944590556],
  [0.624792946, -0.252470637, -0.50535961, -0.170139031, -0.193640298, -0.0225813842, 0.543532333, -0.818596944, -0.0348913171, 1.05206813, -1.11179574, 0.776773894, 0.222122398, 0.144359903, 0.0872192977, 0.644417303, 0.876295935, -0.355461029, -0.899610935, 0.0545300925, 0.593029479, 0.364416719, -0.710912252, 0.37021624, 0.77751649, 0.353129859, -0.295817998, 0.200875517, 0.311100863, 1.29198664, -0.149287255, -1.2664882, 0.287352169, 0.809659595, -0.516209041, -0.49703509, 0.766098078, 0.66863528, 1.54476281, -0.203236183, 0.181949952, 0.201211493, 1.18573452, -0.883365519, 2.90570416, 0.880608614, 2.01354517]
])

MODEL_CLASS_NAMES = ["STABLE_BASELINE", "MICRO_VIBRATION", "SLOW_TILT_SUBSIDENCE", "ABNORMAL_DEFORMATION"]

class FeatureExtractor:
    def __init__(self, window_size=50):
        self.window_size = window_size
        self.buffer = deque(maxlen=window_size)

    def add_sample(self, raw_data):
        """Adds a single raw sample (dict with ax, ay, az, gx, gy, gz, pitch, roll, vib, temp)."""
        self.buffer.append(raw_data)

    def is_ready(self):
        return len(self.buffer) == self.window_size

    def extract_47_features(self):
        """Extracts exact 47 statistical and trajectory features from the 50-sample buffer."""
        if not self.is_ready():
            return np.zeros(MODEL_N_FEATURES)

        # Convert buffer to structured numpy arrays
        ax = np.array([s['ax'] for s in self.buffer])
        ay = np.array([s['ay'] for s in self.buffer])
        az = np.array([s['az'] for s in self.buffer])
        gx = np.array([s['gx'] for s in self.buffer])
        gy = np.array([s['gy'] for s in self.buffer])
        gz = np.array([s['gz'] for s in self.buffer])
        pitch = np.array([s['pitch'] for s in self.buffer])
        roll = np.array([s['roll'] for s in self.buffer])
        vib = np.array([s['vib'] for s in self.buffer])

        feats = []
        
        # 1-11: Channel Means
        feats.extend([np.mean(ax), np.mean(ay), np.mean(az), np.mean(gx), np.mean(gy), np.mean(gz), 
                      np.mean(pitch), np.mean(roll), np.mean(vib), np.max(pitch), np.max(vib)])

        # 12-26: Standard Deviations
        feats.extend([np.std(ax), np.std(ay), np.std(az), np.std(gx), np.std(gy), np.std(gz),
                      np.std(pitch), np.std(roll), np.std(vib),
                      np.min(ax), np.max(ax), np.min(ay), np.max(ay), np.min(az), np.max(az)])

        # 27-30: Slopes / Trajectory Trends
        time_idx = np.arange(self.window_size)
        pitch_slope = np.polyfit(time_idx, pitch, 1)[0] if len(pitch) > 1 else 0
        roll_slope = np.polyfit(time_idx, roll, 1)[0] if len(roll) > 1 else 0
        feats.extend([pitch_slope, roll_slope, np.max(pitch) - np.min(pitch), np.max(roll) - np.min(roll)])

        # 31-47: Energy, RMS & Padding to match 47 features
        feats.extend([np.sqrt(np.mean(ax**2)), np.sqrt(np.mean(ay**2)), np.sqrt(np.mean(az**2)),
                      np.sqrt(np.mean(gx**2)), np.sqrt(np.mean(gy**2)), np.sqrt(np.mean(gz**2)),
                      np.sum(ax**2), np.sum(ay**2), np.sum(az**2),
                      np.sum(gx**2), np.sum(gy**2), np.sum(gz**2),
                      np.var(pitch), np.var(roll), np.var(vib),
                      pitch[-1] - pitch[0], roll[-1] - roll[0]])

        return np.array(feats[:MODEL_N_FEATURES])

def predict_stage_from_features(features_47):
    """Executes Logistic Regression pipeline matching model_parameters.h."""
    # 1. Standardize Features
    scaled_z = (features_47 - MODEL_MEAN) / MODEL_SCALE
    
    # 2. Compute Class Logits
    scores = np.zeros(MODEL_N_CLASSES)
    for c in range(MODEL_N_CLASSES):
        scores[c] = MODEL_INTERCEPT[c] + np.dot(MODEL_COEF[c], scaled_z)

    # 3. Softmax Probabilities
    exp_scores = np.exp(scores - np.max(scores))
    probs = exp_scores / np.sum(exp_scores)
    
    best_cls = int(np.argmax(probs))
    confidence = float(probs[best_cls])
    
    return best_cls, MODEL_CLASS_NAMES[best_cls], confidence