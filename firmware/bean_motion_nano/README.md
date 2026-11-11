# BEAN motion: Jetson USB serial to Arduino Nano + PCA9685

This is a PWM-output adapter for the **existing** BEAN BodyRegistry, MotionSafety and MotionCommand path. It does not replace BEAN's learning, teaching, or simulation modules. The Nano sketch needs the Adafruit PWM Servo Driver library. USB serial baud rate: 115200. PCA9685 I2C address: 0x40, update frequency: 50 Hz.

## Calibrate your existing hardware

Copy the *real robot's* body registry to a **local, untracked** body_registry.json. For each wired joint, set its channel (0..15), hardware_connected: true, and measured mechanical limits. The repository example intentionally has no enabled hardware. Keep a separate local pulse calibration JSON mapping joint IDs to pulse_at_min_us and pulse_at_max_us: these correspond to the registry's absolute min/max joint positions, not generalized servo defaults. Protocol accepts 500..2500 microseconds. Reverse endpoints for inverted joints.

Example **format only**, not actual calibration for BEAN:

~~~json
{"left_finger_curl": {"pulse_at_min_us": 800, "pulse_at_max_us": 2100}}
~~~

Flash bean_motion_nano.ino to the Nano with the Adafruit PWM Servo Driver library installed. Supply servo power separately and share ground according to the PCA9685 wiring instructions. Start calibration with unobstructed limbs.

On Jetson, with USB-connected Nano:

~~~sh
python -m pip install pyserial
python -m bean.motion.arduino_bridge --port /dev/ttyUSB0 \
  --body /path/to/body_registry.json \
  --calibration /path/to/servo_calibration.json \
  --joint left_finger_curl --position 30 --speed 10
~~~

Output includes accepted_by_controller: true and position_confirmed: false. **Arduino ACK only confirms that the PWM request was handed to the PCA9685.** No sensor has confirmed actual travel, grasp or completion. In v1, speed is checked against BEAN's joint limits but **does not yet regulate physical motion velocity**. Commands move one servo target at a time; coordinated trajectories, visual reaching, and feedback-driven pickup are further integrations, not claimed functionality.

Synthetic tests: python -m pytest bean/tests/test_arduino_bridge.py. The Arduino sketch and hardware path require independent compilation and bench testing on the actual Nano/Jetson before calling them verified.
