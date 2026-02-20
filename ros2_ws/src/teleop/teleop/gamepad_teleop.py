#!/usr/bin/env python3
"""
gamepad_teleop.py

Name: Frank E Cortez
Course: ENGR 857
File: gamepad_teleop.py

Description:
  Safe gamepad teleoperation node for QBot:

  Required features:
    a) Hold RB while moving is half speed
    b) Press X to stop and shutdown teleop node
    c) LED color indicates motion direction:
         - Green  = moving forward
         - Blue   = moving backward
         - Yellow = stationary
         
"""

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist
from std_msgs.msg import ColorRGBA


class GamepadTeleop(Node):
    """ROS2 node that converts Joy messages into cmd_vel and LED commands."""

    def __init__(self):
        super().__init__('gamepad_teleop')

        self.joy_topic = '/joy'
        self.cmd_vel_topic = '/cmd_vel'

        #    ros2 topic info /qbot_led
        self.led_topic = '/qbot_led_strip'

        
        # Controller Mapping
    
        # Left stick: axes[0] = left/right, axes[1] = up/down
        self.axis_linear = 1     # vertical
        self.axis_angular = 0    # horizontal

        # Buttons (F710 in XInput mode usually):
        self.btn_x = 2           # X button
        self.btn_rb = 5          # RB

    
        self.max_linear = 1.0
        self.max_angular = 1.0
        self.deadband = 0.10   
        self.half_speed_scale = 0.5

        self.cmd_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        self.led_pub = self.create_publisher(ColorRGBA, self.led_topic, 10)
        self.create_subscription(Joy, self.joy_topic, self.joy_cb, 10)

        self.get_logger().info("GamepadTeleop started")
        self.get_logger().info(f" joy_topic={self.joy_topic}")
        self.get_logger().info(f" cmd_vel_topic={self.cmd_vel_topic}")
        self.get_logger().info(f" led_topic={self.led_topic} (ColorRGBA)")
        self.get_logger().info(
            f" mapping: axis_linear={self.axis_linear}, axis_angular={self.axis_angular}, "
            f"btn_rb={self.btn_rb}, btn_x={self.btn_x}"
        )

    @staticmethod
    def _apply_deadband(value: float, deadband: float) -> float:
        """Zero out small joystick values to prevent drift."""
        return 0.0 if abs(value) < deadband else value

    def _publish_led(self, r: float, g: float, b: float, a: float = 1.0):
        """Publish LED ColorRGBA."""
        msg = ColorRGBA()
        msg.r = float(r)
        msg.g = float(g)
        msg.b = float(b)
        msg.a = float(a)
        self.led_pub.publish(msg)

    def _stop_robot(self):
        """Publish zero velocity command."""
        t = Twist()
        t.linear.x = 0.0
        t.angular.z = 0.0
        self.cmd_pub.publish(t)

    def joy_cb(self, msg: Joy):
        """Callback for joystick messages."""

        if len(msg.axes) <= max(self.axis_linear, self.axis_angular):
            self.get_logger().warn("Joy message does not contain expected axes indices")
            return

        # left stick read 
        raw_linear = msg.axes[self.axis_linear]
        raw_angular = msg.axes[self.axis_angular]

        # Your setup pushing forward
        linear = raw_linear
        angular = raw_angular

        # Apply deadband
        linear = self._apply_deadband(linear, self.deadband)
        angular = self._apply_deadband(angular, self.deadband)

        # Buttons safety rb and x 
        rb = msg.buttons[self.btn_rb] if len(msg.buttons) > self.btn_rb else 0
        x = msg.buttons[self.btn_x] if len(msg.buttons) > self.btn_x else 0

        # Kill signal (X)
        if x:
            self.get_logger().warn("KILL pressed: stopping robot and shutting down teleop node.")
            self._stop_robot()
            self._publish_led(1.0, 0.0, 0.0, 1.0)
            rclpy.shutdown()
            return
        scale = self.half_speed_scale if rb else 1.0
        
        
        twist = Twist()
        twist.linear.x = linear * self.max_linear * scale
        twist.angular.z = angular * self.max_angular * scale

        self.cmd_pub.publish(twist)

        # LED color direction 

        if twist.linear.x > 0.05:
            self._publish_led(0.0, 1.0, 0.0, 1.0)   # Green
        elif twist.linear.x < -0.05:
            self._publish_led(0.0, 0.0, 1.0, 1.0)   # Blue
        else:
            self._publish_led(1.0, 1.0, 0.0, 1.0)   # Yellow


def main(args=None):
    rclpy.init(args=args)
    node = GamepadTeleop()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
