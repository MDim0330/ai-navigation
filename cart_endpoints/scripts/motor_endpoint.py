#!/usr/bin/env python

import serial
import rospy
import bitstruct
from navigation_msgs.msg import VelAngle
from std_msgs.msg import Int8, Bool, Float32
import time
import math
cart_port = '/dev/ttyUSB9' #hardcoded depending on computer

# STATES:
MOVING = 0 
BRAKING = 1
STOPPED = 2

# Speed Dial Max
MAX_SPEED_VOLTAGE = float(650)

class MotorEndpoint(object):

    def __init__(self):
        global cart_port
        self.current_speed = 0.0
        self.new_vel = True
        self.debug = False
        self.stop = False
        self.gentle_stop = False
        self.delay_print = 0
        self.brake = int(0)
        self.drove_since_braking = True
        self.cmd_msg = None
        self.arduino_message = "Not empty"
        # Time (seconds) to ramp up to full brakes
        self.brake_time = 3
        self.node_rate = 10
        self.state = STOPPED
        self.stopping_time = 0
        self.step_size = 255.0/(self.node_rate*self.brake_time)
        self.obstacle_distance = -1
        self.brake_time_used = 0
        self.comfortable_stop_dist = 4.0
        # init local values to store & change msg params
        self.vel_curr = 0
        self.vel_curr_cart_units = 0
        self.vel = 0
        self.vel_cart_units = 0
        self.angle = 0
        self.steering_tolerance = 50 # default was 45
        """ Set up the node. """
        rospy.init_node('motor_endpoint')
        rospy.loginfo("Starting motor node!")
        # Connect to arduino serial port
        try:
            self.serial_port = serial.Serial(cart_port, 57600, write_timeout=0)
        except Exception as e:
            print( "Motor_endpoint: " + str(e))
            rospy.logerr("Motor_endpoint: " + str(e))

        rospy.loginfo("Speed serial established")
        """
        Connect to arduino for steering
        """
        self.motion_subscriber = rospy.Subscriber('/nav_cmd', VelAngle, self.motion_callback,
                                                  queue_size=10)
        self.debug_subscriber = rospy.Subscriber('/realtime_debug_change', Bool, self.debug_callback, queue_size=10)
        """
        Speed changing topics
        """
        # self.ui_speed = rospy.Subscriber('/speed_setting', Float32, self.ChangeCartSpeed)
        
        self.change_vel = rospy.Publisher('/speed', Float32, queue_size=1)
        # Give serial port 1 second to buffer
        #time.sleep(1)

        rate = rospy.Rate(self.node_rate)
        while not rospy.is_shutdown():
            if self.cmd_msg is not None:
                self.speed_dial_process()
                self.endpoint_calc()
            rate.sleep()

    def motion_callback(self, planned_vel_angle):
        self.cmd_msg = planned_vel_angle

        # set local velocity from msg values
        self.vel_curr = self.cmd_msg.vel_curr
        self.vel = self.cmd_msg.vel
        self.angle = self.cmd_msg.angle

        if self.vel < 0:
            # indicates an obstacle
            self.obstacle_distance = abs(self.vel)
            self.vel = 0
        else:
            # reset obstacle distance and brake time
            self.obstacle_distance = -1
            self.brake_time_used = 0
            self.full_stop_count = 0

        if self.vel > 0 and (self.state == STOPPED or self.state == BRAKING) and (time.time()- self.stopping_time) > 10:
            self.state = MOVING
            self.brake = 0 # make sure we take the foot off the brake

        elif self.state == MOVING and self.vel <= 0:  # Brakes are hit
            self.state = BRAKING
            self.brake = 0 # ramp up braking from 0
            self.stopping_time = time.time()
            
        self.new_vel = True     

    def debug_callback(self, msg):
        self.debug = msg.data


    def endpoint_calc(self):
        if self.new_vel:
            #The first time we get a new target speed and angle we must convert it        
            self.vel_cart_units = self.vel
            self.vel_curr_cart_units = self.vel_curr

            self.new_vel = False

            self.vel_cart_units *= 50       # Rough conversion from m/s to cart controller units
            self.vel_curr_cart_units *= 50  # Rough conversion from m/s to cart controller units
            if self.vel_cart_units > 254:
                self.vel_cart_units = 254
            if self.vel_cart_units < -254:
                self.vel_cart_units = -254
            if self.vel_curr_cart_units > 254:
                self.vel_curr_cart_units = 254
            if self.vel_cart_units < 0:
                rospy.logwarn("NEGATIVE VELOCITY REQUESTED FOR THE MOTOR ENDPOINT!")
        
        target_speed = int(self.vel_cart_units) #float64
        current_speed = int(self.vel_curr_cart_units) #float64

        #adjust the target_angle range from (-45 <-> 45) to (0 <-> 100)
        # rospy.loginfo("Angle before adjustment: " + str(self.cmd_msg.angle))

        if(self.angle < -40):
            self.angle = self.steering_tolerance * -1
        if(self.angle > 40):
            self.angle = self.steering_tolerance
        target_angle = 100 - int(( (self.angle + self.steering_tolerance) / 90 ) * 100)
        
        #if debug printing is requested print speed and angle info
        if self.debug:
            self.delay_print -= 1
            if self.delay_print <= 0:
                self.delay_print = 5
                rospy.loginfo("Endpoint Angle: " + str(target_angle))
                rospy.loginfo("Endpoint Speed: " + str(target_speed))

        if self.state == STOPPED:
            self.brake = 0
            target_speed = 0
        elif self.state == BRAKING:
            if self.obstacle_distance > 0:
                # there exists an obstacle in the cart's path we need to stop for
               
                self.brake_time_used += (1.0/self.node_rate) # 1 sec / rate per sec (10)
                obstacle_brake_time = self.obstacle_distance/self.vel_curr - (1.0/self.node_rate) # we decrease by one node rate initially to account for rounding
                
                y = (0.1) * ((2550) ** (self.brake_time_used/obstacle_brake_time))

                if (y >= 255):
                    self.full_stop_count += 1

                self.brake = float(min(255, math.ceil(y)))
            else:
                # comfortable stop, no obstacle/deadline given

                self.brake_time_used += (1.0/self.node_rate) # 1 sec / rate per sec (10)
                brake_time = self.comfortable_stop_dist - (1.0/self.node_rate) # we decrease by one node rate initially to account for rounding
                
                y = (0.1) * ((2550) ** (self.brake_time_used/brake_time))

                if (y >= 255):
                    self.full_stop_count += 1

                self.brake = float(min(255, math.ceil(y)))
            if self.brake >= 255 and self.full_stop_count > 10:  # We have reached maximum braking!
                self.state = STOPPED
                # reset brake time used
                self.brake_time_used = 0
                self.full_stop_count = 0
            target_speed = 0

        self.pack_send(target_speed, int(self.brake), target_angle)
    
    def pack_send(self, throttle, brake, steer_angle):
        data = bytearray(b'\x00' * 5)
        bitstruct.pack_into('u8u8u8u8u8', data, 0, 42, 21, abs(throttle), brake, steer_angle + 10)
        self.serial_port.write(data)
        
    def speed_dial_process(self):
        try:
            #time.sleep(1)
            self.arduino_message = self.serial_port.readline()
            #self.arduino_message = self.serial_port.read(self.serial_port.inWaiting() + 32) 
            # self.serial_port.reset_output_buffer()
            rospy.loginfo("Message recieved: %s", self.arduino_message)
            if self.arduino_message == "":
                rospy.loginfo("Arduino message processed but no contents\n")
            else:
                # An array of strings in current format - [Steering, Throttle, Brake, SpeedDial]
                # no longer the case currently returns just string with speed dial data
                # string_data = self.arduino_message.split(",")
                rospy.loginfo("I recieved a message\n")
            # Only reading SpeedDial data currently
                # rospy.loginfo(arduino_message)
                speed_dial_data = int(self.arduino_message)

            # Conversion Equation
            speed_normalization = 8 * (speed_dial_data / MAX_SPEED_VOLTAGE)
            # self.change_vel.publish(speed_normalization)

        except Exception as e:
            # Sleep and try again
            #time.sleep(5)
            rospy.loginfo("** Exception *** --- Broken Message: %s", self.arduino_message) 
            print(e) 
    def ChangeCartSpeed(self, msg):
        self.change_vel.publish(msg.data)

if __name__ == "__main__":
    try:
        MotorEndpoint()
    except rospy.ROSInterruptException:
        pass
