#!/usr/bin/env python
# Software License Agreement (BSD License)
#
# Author: Chris L8 https://github.com/chrisl8
# URL: https://github.com/chrisl8/ArloBot

import rospy
import tf
import sys
import time

from std_msgs.msg import String
from std_msgs.msg import Bool

#For USB relay board
from pylibftdi import BitBangDevice

# From:
# ----------------------------------------------------------------------------
#   
#   DRCONTROL.PY
#   
#   Copyright (C) 2012 Sebastian Sjoholm, sebastian.sjoholm@gmail.com
#   
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#   
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#   
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#   
#   Version history can be found at 
#   http://code.google.com/p/drcontrol/wiki/VersionHistory
#
#   $Rev$
#   $Date$
#
# ----------------------------------------------------------------------------
# For SainSmart 8 port USB model
class relay_data(dict):

    address = {
            "1":"1",
            "2":"2",
            "3":"4",
            "4":"8",
            "5":"10",
            "6":"20",
            "7":"40",
            "8":"80",
            "all":"FF"
            }

    def __getitem__(self, key): return self[key]
    def keys(self): return self.keys()

# ----------------------------------------------------------------------------
# testBit() returns a nonzero result, 2**offset, if the bit at 'offset' is one.
# http://wiki.python.org/moin/BitManipulation
# ----------------------------------------------------------------------------

def testBit(int_type, offset):
    mask = 1 << offset
    return(int_type & mask)

# For SainSmart 8 port USB model
def get_relay_state( data, relay ):
    if relay == "1":
        return testBit(data, 0)
    if relay == "2":
        return testBit(data, 1)
    if relay == "3":
        return testBit(data, 2)
    if relay == "4":
        return testBit(data, 3)
    if relay == "5":
        return testBit(data, 4)
    if relay == "6":
        return testBit(data, 5)
    if relay == "7":
        return testBit(data, 6)
    if relay == "8":
        return testBit(data, 7)

class UsbRelay(object):
    '''
    Helper class for communicating with a Propeller board over serial port
    '''

    def __init__(self):
        rospy.init_node('arlobot_usbrelay')
        # http://wiki.ros.org/rospy_tutorials/Tutorials/WritingPublisherSubscriber
        self.r = rospy.Rate(0.25) # 1hz refresh rate

        self.relayExists = rospy.get_param("/arlobot/usbRelayInstalled", False)
        if self.relayExists:
            # Get the relay serial number, we may grab this programatically later
            self.relaySerialNumber = rospy.get_param("/arlobot/usbRelaySerialNumber", "")
            # Get the motor relay numbers, this will be set elsewhere later
            self.leftMotorRelay = rospy.get_param("~usbLeftMotorRelay", "")
            self.rightMotorRelay = rospy.get_param("~usbRightMotorRelay", "")
            '''
            if state == "on" and self._SafeToOperate == 1:
                BitBangDevice(relaySerialNumber).port |= int(relay.address[leftMotorRelay], 16)
                BitBangDevice(relaySerialNumber).port |= int(relay.address[rightMotorRelay], 16)
                self._motorsOn = 1
            elif state == "off":
                BitBangDevice(relaySerialNumber).port &= ~int(relay.address[leftMotorRelay], 16)
                BitBangDevice(relaySerialNumber).port &= ~int(relay.address[rightMotorRelay], 16)
                self._motorsOn = 0
            '''
        else:
            rospy.loginfo("No USB Relay board installed.")

        # Publishers
        self._pirPublisher = rospy.Publisher('~pirState', Bool, queue_size = 1) # publish matrix of USB Relay states

    def Run(self):
        while not rospy.is_shutdown():
            if self.relayExists:
                # Gather USB Relay status for each relay and publish
                for i in range(1,9):
                    state = get_relay_state( BitBangDevice(self.relaySerialNumber).port, str(i) )
                    if state == 0:
                        print "Relay " + str(i) + " state:\tOFF (" + str(state) + ")"
                    else:
                        print "Relay " + str(i) + " state:\tON (" + str(state) + ")"
            '''
            if rospy.has_param('/arlobot/monitorACconnection'): # If arlobot_bringup is running
                checkAC = rospy.get_param('/arlobot/monitorACconnection') # Use parameter from arlobot_bringup to decide if we should monitor AC or not
            else:
                checkAC = True # Otherwise monitor it if arlobot_bringup isn't running
                
            if checkAC: # Unless we were told not to
                #upower -i /org/freedesktop/UPower/devices/line_power_AC
                laptopPowerState = subprocess.Popen(['upower', '-i', '/org/freedesktop/UPower/devices/line_power_AC'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
                for line in iter(laptopPowerState.stdout.readline, ""):
                    #rospy.loginfo(line) # for Debugging
                    if 'online' in line:
                        #rospy.loginfo(line) # Just so we know it is working (for debugging)
                        upowerOutput = line.split()
                        #print upowerOutput[1]
                        if upowerOutput[1] == 'no':
                            if self.acPower: # Only log and set parameters if there is a change!
                                rospy.loginfo("AC Power DISconnected.")
                                self.acPower = False
                                rospy.set_param('~ACpower', self.acPower)
                        elif upowerOutput[1] == 'yes':
                            if self.acPower is False: # Only log and set parameters if there is a change!
                                rospy.loginfo("AC Power Connected.")
                                self.acPower = True
                                rospy.set_param('~ACpower', self.acPower)
                laptopPowerState.stdout.close()
                laptopPowerState.wait()
            else: # Just set to 0 if we were told to ignore AC power status.
                if self.acPower: # Only log and set parameters if there is a change!
                    self.acPower = False
                    rospy.set_param('~ACpower', self.acPower)
            
            # Determine safety status based on what we know
            if self.acPower:
                self.safeToGo = False
            else:
                self.safeToGo = True
            
            self._safetyStatusPublisher.publish(self.safeToGo) # Publish safety status
            '''
            self.r.sleep() # Sleep long enough to maintain the rate set in __init__

    def _HandleReceivedLine(self,  line): # This is Propeller specific
        self._Counter = self._Counter + 1
        #rospy.logdebug(str(self._Counter) + " " + line)
        #if (self._Counter % 50 == 0):
        self._SerialPublisher.publish(String(str(self._Counter) + ", in:  " + line))

        if (len(line) > 0):
            lineParts = line.split('\t')
            if (lineParts[0] == 'o'): # We should broadcast the odometry no matter what. Even if the motors are off, or location is useful!
                self._BroadcastOdometryInfo(lineParts)
                return
            if (lineParts[0] == 'i'):
                self._InitializeDriveGeometry(lineParts)
                return
            if (lineParts[0] == 's'): # Arlo Status info, such as sensors.
                rospy.loginfo("Propeller: " + line)
                return
                
    def _SafetyShutdown(self, safe):
        if safe.data:
            self._SafeToOperate = 1
        else:
            self._SafeToOperate = 0
            if self._motorsOn == 1:
                rospy.loginfo("Safety Shutdown initiated")
                self._SwitchMotors("off")
                # Reset the propeller board, otherwise there are problems if you bring up the motors again while it has been operating
                rospy.loginfo("_SerialDataGateway stopping . . .")
                self._SerialDataGateway.Stop()
                rospy.loginfo("_SerialDataGateway stopped.")
                rospy.loginfo("10 second pause to let Activity Board settle after serial port reset . . .")
                time.sleep(10) # Give it time to settle.
                rospy.loginfo("_SerialDataGateway starting . . .")
                self._SerialDataGateway.Start()
                rospy.loginfo("_SerialDataGateway started.")
                # TODO: There is probably a better way, but this seems to work.

    def _BroadcastOdometryInfo(self, lineParts):
        # If we got this far, we can assume that the Propeller board is initialized and the motors should be on.
        # The _SwitchMotors() function will deal with the _SafeToOparete issue
        if self._motorsOn == 0:
            self._SwitchMotors("on")
        # This broadcasts ALL info from the Propeller based robot every time data comes in
        partsCount = len(lineParts)

        #rospy.logwarn(partsCount)
        if (partsCount  != 8): # Just discard short/long lines, increment this as lines get longer
            pass
        
        try:
            x = float(lineParts[1])
            y = float(lineParts[2])
            # 3 is odom based heading and 4 is gyro based
            theta = float(lineParts[3]) # On ArloBot odometry derived heading works best.
            
            vx = float(lineParts[5])
            omega = float(lineParts[6])
        
            quaternion = Quaternion()
            quaternion.x = 0.0 
            quaternion.y = 0.0
            quaternion.z = sin(theta / 2.0)
            quaternion.w = cos(theta / 2.0)
            
            
            rosNow = rospy.Time.now()
            
            # First, we'll publish the transform from frame odom to frame base_link over tf
            # Note that sendTransform requires that 'to' is passed in before 'from' while
            # the TransformListener' lookupTransform function expects 'from' first followed by 'to'.
            # This transform conflicts with transforms built into the Turtle stack
            # http://wiki.ros.org/tf/Tutorials/Writing%20a%20tf%20broadcaster%20%28Python%29
            # This is done in/with the robot_pose_ekf because it can integrate IMU/gyro data
            # using an "extended Kalman filter"
            # REMOVE this "line" if you use robot_pose_ekf
            self._OdometryTransformBroadcaster.sendTransform(
                (x, y, 0), 
                (quaternion.x, quaternion.y, quaternion.z, quaternion.w),
                rosNow,
                "base_footprint",
                "odom"
                )

            # next, we will publish the odometry message over ROS
            odometry = Odometry()
            odometry.header.frame_id = "odom"
            odometry.header.stamp = rosNow
            odometry.pose.pose.position.x = x
            odometry.pose.pose.position.y = y
            odometry.pose.pose.position.z = 0
            odometry.pose.pose.orientation = quaternion

            odometry.child_frame_id = "base_link"
            odometry.twist.twist.linear.x = vx
            odometry.twist.twist.linear.y = 0
            odometry.twist.twist.angular.z = omega
            
            # Save last X, Y and Heading for reuse if we have to reset:
            self.lastX = x
            self.lastY = y
            self.lastHeading = theta

            # robot_pose_ekf needs these covariances and we may need to adjust them.
            # From: ~/turtlebot/src/turtlebot_create/create_node/src/create_node/covariances.py
            # However, this is not needed because we are not using robot_pose_ekf
            '''
            odometry.pose.covariance = [1e-3, 0, 0, 0, 0, 0,
                                    0, 1e-3, 0, 0, 0, 0,
                                    0, 0, 1e6, 0, 0, 0,
                                    0, 0, 0, 1e6, 0, 0,
                                    0, 0, 0, 0, 1e6, 0,
                                    0, 0, 0, 0, 0, 1e3]

            odometry.twist.covariance = [1e-3, 0, 0, 0, 0, 0,
                                     0, 1e-3, 0, 0, 0, 0,
                                     0, 0, 1e6, 0, 0, 0,
                                     0, 0, 0, 1e6, 0, 0,
                                     0, 0, 0, 0, 1e6, 0,
                                     0, 0, 0, 0, 0, 1e3]
                                     '''

            self._OdometryPublisher.publish(odometry)

            # Joint State for Turtlebot stack
            # Note without this transform publisher the wheels will
            # be white, stuck at 0, 0, 0 and RVIZ will tell you that
            # there is no transform from the wheel_links to the base_
            '''
            # Instead of publishing a stream of pointless transforms,
            # How about if I just make the joint static in the URDF?
            # create.urdf.xacro:
            # <joint name="right_wheel_joint" type="fixed">
            # NOTE This may prevent Gazebo from working with this model
            js = JointState(name = ["left_wheel_joint", "right_wheel_joint", "front_castor_joint", "back_castor_joint"],
                            position=[0,0,0,0], velocity=[0,0,0,0], effort=[0,0,0,0])
            js.header.stamp = rosNow
            self.joint_states_pub.publish(js)
            '''

            # Fake laser from "PING" Ultrasonic Sensor and IR Distance Sensor input:
            # http://wiki.ros.org/navigation/Tutorials/RobotSetup/TF
            '''
            Use:
            roslaunch arlobot_rviz_launchers view_robot.launch
            to view this well for debugging and testing.
            The purpose of this is two fold:
            1. It REALLY helps adjusting values in the Propeller and ROS when I can visualize the sensor output in RVIZ!
                For this purpose, a lot of the parameters are a matter of personal taste. Whatever makes it easiest to visualize is best.
            2. I want to allow AMCL to use this data to avoid obstacles that the Kinect/Xtion miss.
                For the second purpose, some of the parameters here may need to be tweaked, to adjust how large an object looks to AMCL.
            Note that we should also adjust the distance at which AMCL takes this data into account either here or elsewhere.
            '''
            # Transform: http://wiki.ros.org/tf/Tutorials/Writing%20a%20tf%20broadcaster%20%28Python%29
            '''
            We do not need to broadcast a transform,
            because it is static and contained within the URDF files now.
            self._SonarTransformBroadcaster.sendTransform(
                (0.1, 0.0, 0.2), 
                (0, 0, 0, 1),
                rosNow,
                "sonar_laser",
                "base_link"
                )
                '''
            # Some help: http://books.google.com/books?id=2ZL9AAAAQBAJ&pg=PT396&lpg=PT396&dq=fake+LaserScan+message&source=bl&ots=VJMfSYXApG&sig=s2YgiHTA3i1OjVyPxp2aAslkW_Y&hl=en&sa=X&ei=B_vDU-LkIoef8AHsooHICA&ved=0CG0Q6AEwCQ#v=onepage&q=fake%20LaserScan%20message&f=false
            # Question: I'm doing this all in degrees and then converting to Radians later. Is there any way to do this in Radians? I just don't know how to create and fill an array with "Radians" since they are not rational numbers, but multiples of PI. Thus the degrees
            num_readings = 360 # How about 1 per degree?
            #num_reeading_multiple = 2 # We have to track this so we know where to put the readings!
            #num_readings = 360 * num_reeading_multiple # I am getting "artifacts" in the global cost map where points fail to clear, even though they clear from the local. Maybe we need a higher resolution?
            laser_frequency = 100 # I'm not sure how to decide what to use here.
            artificialFarDistance = 10 # This is the fake distance to set all empty slots, and slots we consider "out of range"
            #ranges = [1] * num_readings # Fill array with fake "1" readings for testing
            PINGranges = [artificialFarDistance] * num_readings # Fill array with artificialFarDistance (not 0) and then overlap with real readings
            # If we use 0, then it won't clear the obstacles when we rotate away, because costmap2d ignores 0's and Out of Range!
            IRranges = [artificialFarDistance] * num_readings # Fill array with artificialFarDistance (not 0) and then overlap with real readings
            '''
            New idea here:
            First, I do not think that this can be used for reliable for map generation.
            If your room as objects that the Kinect
            cannot map, then you will probably need to modify the room (cover mirrors, etc.) or try
            other laser scanner options.
            SO, since we only want to use it for cost planning, we should massage the data, because
            it is easy for it to get bogged down with a lot of "stuff" everywhere.
            
            From: http://answers.ros.org/question/11446/costmaps-obstacle-does-not-clear-properly-under-sparse-environment/
            "When clearing obstacles, costmap_2d only trusts laser scans returning a definite range.
            Indoors, that makes sense. Outdoors, most scans return max range, which does not clear
            intervening obstacles. A fake scan with slightly shorter ranges can be constructed that
            does clear them out."
            SO, we need to set all "hits" above the distance we want to pay attention to to a distance very far away,
            but just within the range_max (which we can set to anything we want), otherwise costmap will not clear items!
            Also, 0 does not clear anything! So if we rotate, then it gets 0 at that point, and ignores it,
            so we need to fill the unused slots with long distances.
            NOTE: This does cause a "circle" to be drawn around the robot, but it shouldn't be a problem because we set
            artificialFarDistance to a distance greater than the planner uses.
            So while it clears things, it shouldn't cause a problem, and the Kinect should override it for things
            in between.
            
            Use:
            roslaunch arlobot_rviz_launchers view_robot.launch
            to view this well for debugging and testing.
            '''
            # Note that sensor orientation is important here! If you have a different number or aim them differently this will not work!
            # TODO: Tweak this value based on real measurements! Use both IR and PING sensors.
            sensorOffset = 0.22545 # The offset between the pretend sensor location in the URDF and real location needs to be added to these values. This may need to be tweaked.
            maxRangeAccepted = .5 # This will be the max used range, anything beyond this is set to a far distance.
            '''
            maxRangeAccepted Testing:

            TODO: More tweaking here could be done. I think it is a trade-off, so there is no end to the adjustment that could be done.
            I did a lot of testing with gmappingn while building a map. Obviously this would be slightly different from using a map we don't update.
            It seems there are so many variables here that testing is difficult. We could find one number works great in one situation but is hopeless in another. Having a comprehensive test course to test in multiple modes for every possible value would be great, but I think it would take months! :)

            REMEMBER, the costmap only pays attention out to a certain set for obstacle_range in costmap_common_params.yaml anyway.
            1 - looks good, and works ok. I am afraid that the costmap gets confused though with things popping in and out of sight all of the time, causing undue wandering.
            2 - This producing less wandering due to things popping in and out of the field of view, BUT it also shows that we got odd affects at longer distances. i.e.
                A doorframe almost always has a hit right in the middle of it.
                In hall, there seems to often be a hit in the middle about 1.5 meters out.
            .5 - This works very well to have the PING data ONLY provide obstacle avoidance, and immediately forget about said obstacles.
                This prevents the navigation stack from fighting with the Activity Board code's built in safety stops, and instead navigate around obstacles before the Activity Board code even gets involved (other than to set speed reductions).
                The only down side if if you tell ArloBot to go somewhere that he cannot due to low obstacles, he will try forever. He won't just bounce off of the obstacle,
                but he will keep trying it and then go away, turn around, and try again over and over. He may even start wandering around the facility trying to find another way in,
                but he will eventually come back and try it again.
                I'm not sure what the solution to this is though, because avoiding low lying obstacles and adding low lying features to the map are really two different things.
                I think if this is well tuned to avoid low lying obstacles it probably will not work well for mapping features.
                IF we could map features with the PING sensors, we wouldn't need the 3D sensor. :)
                
                NOTE: The bump sensors on Turtlebot mark but do not clear. I'm not sure how that works out. It seems like every bump would end up being a "blot" in the landscape never to be returned to, but maybe there is something I am missing?
                
            NOTE: Could this be different for PING vs. IR?
            Currently I'm not using IR! Just PING. The IR is not being used by costmap. It is here for seeing in RVIZ, and the Propeller board uses it for emergency stopping,
            but costmap isn't watching it at the moment. I think it is too erratic for that.
            '''
            pingRange0 = (int(lineParts[7]) / 100.0) + sensorOffset # Convert cm to meters and add offset
            if pingRange0 > maxRangeAccepted: # Set to "out of range" for distances over 1 meter to clear long range obstacles and use this for short tmer only.
                pingRange0 = artificialFarDistance # Be sure "ultrasonic_scan.range_max" set above this or costmap will ignore these and not clear the cost map!
            irRange0 = (int(lineParts[8]) / 100.0) + sensorOffset # Convert cm to meters and add offset
            pingRange1 = (int(lineParts[9]) / 100.0) + sensorOffset
            if pingRange1 > maxRangeAccepted:
                pingRange1 = artificialFarDistance
            irRange1 = (int(lineParts[10]) / 100.0) + sensorOffset
            pingRange2 = (int(lineParts[11]) / 100.0) + sensorOffset # Center forward sensor.
            if pingRange2 > maxRangeAccepted:
                pingRange2 = artificialFarDistance
            irRange2 = (int(lineParts[12]) / 100.0) + sensorOffset # Center forward sensor.
            pingRange3 = (int(lineParts[13]) / 100.0) + sensorOffset
            if pingRange3 > maxRangeAccepted:
                pingRange3 = artificialFarDistance
            irRange3 = (int(lineParts[14]) / 100.0) + sensorOffset
            pingRange4 = (int(lineParts[15]) / 100.0) + sensorOffset
            if pingRange4 > maxRangeAccepted:
                pingRange4 = artificialFarDistance
            irRange4 = (int(lineParts[16]) / 100.0) + sensorOffset
            pingRange5 = (int(lineParts[17]) / 100.0) + sensorOffset # Rear sensor, note these numbers can change if you add more sensors!
            if pingRange5 > maxRangeAccepted:
                pingRange5 = artificialFarDistance
            irRange5 = (int(lineParts[18]) / 100.0) + sensorOffset # Rear sensor, note these numbers can change if you add more sensors!
            # I'm going to start by just kind of "filling in" the area with the data and then adjust based on experimentation.
            '''
            The sensors are 11cm from center to center at the front of the base plate.
            The radius of the base plate is 22.545 cm
            = 28 degree difference (http://ostermiller.org/calc/triangle.html)
            '''
            sensorSeperation = 28
            
            # Spread code:
            '''
            # "sensorSpread" is how wide we expand the sensor "point" in the fake laser scan.
            # For the purpose of obstacle avoidance, I think this can actually be a single point,
            # Since the costmap inflates these anyways.

            #One issue I am having is it seems that the "ray trace" to the maximum distance
            #may not line up with near hits, so that the global cost map is not being cleared!
            #Switching from a "spread" to a single point may fix this?
            #Since the costmap inflates obstacles anyway, we shouldn't need the spead should we?

            #sensorSpread = 10 # This is how wide of an arc (in degrees) to paint for each "hit"
            #sensorSpread = 2 # Testing. I think it has to be even numbers?
            #TODO: Should this be smaller?! It might help. Need to test more.

            #NOTE:
            #This assumes that things get bigger as they are further away. This is true of the PING's area,
            #and while it may or may not be true of the object the PING sees, we have no way of knowing if
            #the object fills the ping's entire field of view or only a small part of it, a "hit" is a "hit".
            #However for the IR sensor, the objects are points, that are the same size regardless of distance,
            #so we are clearly inflating them here.

            for x in range(180 - sensorSpread / 2, 180 + sensorSpread / 2):
                PINGranges[x] = pingRange5 # Rear Sensor
                IRranges[x] = irRange5 # Rear Sensor

            for x in range((360 - sensorSeperation * 2) - sensorSpread / 2, (360 - sensorSeperation * 2) + sensorSpread / 2):
                PINGranges[x] = pingRange4
                IRranges[x] = irRange4

            for x in range((360 - sensorSeperation) - sensorSpread / 2, (360 - sensorSeperation) + sensorSpread / 2):
                PINGranges[x] = pingRange3
                IRranges[x] = irRange3

            for x in range(360 - sensorSpread / 2, 360):
                PINGranges[x] = pingRange2
                IRranges[x] = irRange2
            # Crosses center line
            for x in range(0, sensorSpread /2):
                PINGranges[x] = pingRange2
                IRranges[x] = irRange2
            
            for x in range(sensorSeperation - sensorSpread / 2, sensorSeperation + sensorSpread / 2):
                PINGranges[x] = pingRange1
                IRranges[x] = irRange1
            
            for x in range((sensorSeperation * 2) - sensorSpread / 2, (sensorSeperation * 2) + sensorSpread / 2):
                PINGranges[x] = pingRange0
                IRranges[x] = irRange0
            '''
            
            # Single Point code:
            #for x in range(180 - sensorSpread / 2, 180 + sensorSpread / 2):
            PINGranges[180] = pingRange5 # Rear Sensor
            IRranges[180] = irRange5 # Rear Sensor

            #for x in range((360 - sensorSeperation * 2) - sensorSpread / 2, (360 - sensorSeperation * 2) + sensorSpread / 2):
            PINGranges[360 - sensorSeperation * 2] = pingRange4
            IRranges[360 - sensorSeperation * 2] = irRange4

            #for x in range((360 - sensorSeperation) - sensorSpread / 2, (360 - sensorSeperation) + sensorSpread / 2):
            PINGranges[360 - sensorSeperation] = pingRange3
            IRranges[360 - sensorSeperation] = irRange3

            #for x in range(360 - sensorSpread / 2, 360):
            #PINGranges[x] = pingRange2
            #IRranges[x] = irRange2
            # Crosses center line
            #for x in range(0, sensorSpread /2):
            PINGranges[0] = pingRange2
            IRranges[0] = irRange2
            
            #for x in range(sensorSeperation - sensorSpread / 2, sensorSeperation + sensorSpread / 2):
            PINGranges[sensorSeperation] = pingRange1
            IRranges[sensorSeperation] = irRange1
            
            #for x in range((sensorSeperation * 2) - sensorSpread / 2, (sensorSeperation * 2) + sensorSpread / 2):
            PINGranges[sensorSeperation * 2] = pingRange0
            IRranges[sensorSeperation * 2] = irRange0
            

            # LaserScan: http://docs.ros.org/api/sensor_msgs/html/msg/LaserScan.html
            ultrasonic_scan = LaserScan()
            infrared_scan = LaserScan()
            ultrasonic_scan.header.stamp = rosNow
            infrared_scan.header.stamp = rosNow
            ultrasonic_scan.header.frame_id = "ping_sensor_array"
            infrared_scan.header.frame_id = "ir_sensor_array"
            # For example:
            #scan.angle_min = -45 * M_PI / 180; // -45 degree
            #scan.angle_max = 45 * M_PI / 180;   // 45 degree
            # if you want to receive a full 360 degrees scan, you should try setting min_angle to -pi/2 and max_angle to 3/2 * pi.
            # Radians: http://en.wikipedia.org/wiki/Radian#Advantages_of_measuring_in_radians
            ultrasonic_scan.angle_min = 0
            infrared_scan.angle_min = 0
            #ultrasonic_scan.angle_max = 2 * 3.14159 # Full circle # Letting it use default, which I think is the same.
            #infrared_scan.angle_max = 2 * 3.14159 # Full circle # Letting it use default, which I think is the same.
            #ultrasonic_scan.scan_time = 3 # I think this is only really applied for 3D scanning
            #infrared_scan.scan_time = 3 # I think this is only really applied for 3D scanning
            # Make sure the part you divide by num_readings is the same as your angle_max!
            # Might even make sense to use a variable here?
            ultrasonic_scan.angle_increment = (2 * 3.14) / num_readings
            infrared_scan.angle_increment = (2 * 3.14) / num_readings
            ultrasonic_scan.time_increment = (1 / laser_frequency) / (num_readings)
            infrared_scan.time_increment = (1 / laser_frequency) / (num_readings)
            # From: http://www.parallax.com/product/28015
            # Range: approximately 1 inch to 10 feet (2 cm to 3 m)
            # This should be adjusted based on the imaginary distance between the actual laser
            # and the laser location in the URDF file.
            ultrasonic_scan.range_min = 0.02 # in Meters Distances below this number will be ignored REMEMBER the offset!
            infrared_scan.range_min = 0.02 # in Meters Distances below this number will be ignored REMEMBER the offset!
            # This has to be above our "artificialFarDistance", otherwise "hits" at artificialFarDistance will be ignored,
            # which means they will not be used to clear the cost map!
            ultrasonic_scan.range_max = artificialFarDistance + 1 # in Meters Distances above this will be ignored
            infrared_scan.range_max = artificialFarDistance + 1 # in Meters Distances above this will be ignored
            ultrasonic_scan.ranges = PINGranges
            infrared_scan.ranges = IRranges
            # "intensity" is a value specific to each laser scanner model.
            # It can safely be ignored
            
            self._UltraSonicPublisher.publish(ultrasonic_scan)
            self._InfraredPublisher.publish(infrared_scan)

        except:
            rospy.logwarn("Unexpected error:" + str(sys.exc_info()[0]))

    def _WriteSerial(self, message):
        self._SerialPublisher.publish(String(str(self._Counter) + ", out: " + message))
        self._SerialDataGateway.Write(message)

    def Start(self):
        self._OdomStationaryBroadcaster.Start()
        rospy.loginfo("10 second pause before starting serial gateway to let Activity Board settle if it is resetting already . . .")
        count = 10
        while count > 0:
            rospy.loginfo(count)
            time.sleep(1)
            count -= 1
        rospy.loginfo("_SerialDataGateway starting . . .")
        self._SerialDataGateway.Start()
        rospy.loginfo("_SerialDataGateway started.")

    def Stop(self):
        rospy.loginfo("Stopping")
        
    def _HandleVelocityCommand(self, twistCommand): # This is Propeller specific
        # NOTE: turtlebot_node has a lot of code under its cmd_vel function to deal with maximum and minimum speeds,
        # which are dealt with in ArloBot on the Activity Board itself in the Propeller code.
        """ Handle movement requests. """
        if self._SafeToOperate: # Do not move if it is not self._SafeToOperate
            v = twistCommand.linear.x        # m/s
            omega = twistCommand.angular.z      # rad/s
            #rospy.logdebug("Handling twist command: " + str(v) + "," + str(omega))
            message = 's,%.3f,%.3f\r' % (v, omega)
            #rospy.logdebug("Sending speed command message: " + message)
            self._WriteSerial(message)
        else:
            message= 's,0.0,0.0\r' # Tell it to be still if it is not SafeToOperate
            self._WriteSerial(message)

    def _InitializeDriveGeometry(self, lineParts):
        if self._SafeToOperate:
            trackWidth = rospy.get_param("~driveGeometry/trackWidth", "0")
            distancePerCount = rospy.get_param("~driveGeometry/distancePerCount", "0")
            message = 'd,%f,%f,%f,%f,%f\r' % (trackWidth, distancePerCount, self.lastX, self.lastY, self.lastHeading)
            rospy.logdebug("Sending drive geometry params message: " + message)
            self._WriteSerial(message)
        else:
            if int(lineParts[1]) == 1:
                self._pirPublisher.publish(True)
            else:
                self._pirPublisher.publish(False)

    def _BroadcastStaticOdometryInfo(self):
        # Broadcast last known odometry and transform while propeller board is offline so that ROS can continue to track status
        # Otherwise things like gmapping will fail when we loose our transform and publishing topics
        if self._motorsOn == 0: # Use motor status to decide when to broadcast static odometry:
            x = self.lastX
            y = self.lastY
            theta = self.lastHeading
            vx = 0 # If the motors are off we will assume the robot is still.
            omega = 0 # If the motors are off we will assume the robot is still.
        
            quaternion = Quaternion()
            quaternion.x = 0.0 
            quaternion.y = 0.0
            quaternion.z = sin(theta / 2.0)
            quaternion.w = cos(theta / 2.0)
            
            rosNow = rospy.Time.now()
            
            # First, we'll publish the transform from frame odom to frame base_link over tf
            # Note that sendTransform requires that 'to' is passed in before 'from' while
            # the TransformListener' lookupTransform function expects 'from' first followed by 'to'.
            # This transform conflicts with transforms built into the Turtle stack
            # http://wiki.ros.org/tf/Tutorials/Writing%20a%20tf%20broadcaster%20%28Python%29
            # This is done in/with the robot_pose_ekf because it can integrate IMU/gyro data
            # using an "extended Kalman filter"
            # REMOVE this "line" if you use robot_pose_ekf
            self._OdometryTransformBroadcaster.sendTransform(
                (x, y, 0), 
                (quaternion.x, quaternion.y, quaternion.z, quaternion.w),
                rosNow,
                "base_footprint",
                "odom"
                )

            # next, we will publish the odometry message over ROS
            odometry = Odometry()
            odometry.header.frame_id = "odom"
            odometry.header.stamp = rosNow
            odometry.pose.pose.position.x = x
            odometry.pose.pose.position.y = y
            odometry.pose.pose.position.z = 0
            odometry.pose.pose.orientation = quaternion

            odometry.child_frame_id = "base_link"
            odometry.twist.twist.linear.x = vx
            odometry.twist.twist.linear.y = 0
            odometry.twist.twist.angular.z = omega
            
            self._OdometryPublisher.publish(odometry)

    def _SwitchMotors(self, state):
        relayExists = rospy.get_param("~usbRelayInstalled", False)
        if relayExists:
            # Start Motors
            # For SainSmart 8 port USB model http://www.sainsmart.com/sainsmart-4-channel-12-v-usb-relay-board-module-controller-for-automation-robotics-1.html
            # Note that this is specific to this model, if you want me to code for various models let me know and I can work with you to expand the code
            # to cover more models and add ROS parameters for picking your model.
            class relay(dict):
                address = {
                    "1":"1",
                    "2":"2",
                    "3":"4",
                    "4":"8",
                    "5":"10",
                    "6":"20",
                    "7":"40",
                    "8":"80",
                    "all":"FF"
                    }
            relaySerialNumber = rospy.get_param("~usbRelaySerialNumber", "")
            leftMotorRelay = rospy.get_param("~usbLeftMotorRelay", "")
            rightMotorRelay = rospy.get_param("~usbRightMotorRelay", "")
            if state == "on" and self._SafeToOperate == 1:
                BitBangDevice(relaySerialNumber).port |= int(relay.address[leftMotorRelay], 16)
                BitBangDevice(relaySerialNumber).port |= int(relay.address[rightMotorRelay], 16)
                self._motorsOn = 1
            elif state == "off":
                BitBangDevice(relaySerialNumber).port &= ~int(relay.address[leftMotorRelay], 16)
                BitBangDevice(relaySerialNumber).port &= ~int(relay.address[rightMotorRelay], 16)
                self._motorsOn = 0
        else: # If no automated motor control exists, just set the state blindly.
            if state == "on":
                self._motorsOn = 1
            elif state == "off":
                self._motorsOn = 0

if __name__ == '__main__':
    node = UsbRelay()
    rospy.on_shutdown(node.Stop)
    try:
        node.Run()
    except rospy.ROSInterruptException:
        node.Stop()