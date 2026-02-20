#!/usr/bin/env python3
"""
teleop_node.py
ENGR 857 - HW 3.5

Features:
- RB halves speed
- X kills (stops robot + shuts down node)
- LED color indicates direction:
    Green  = forward
    Blue   = backward
    Yellow = stopped
"""

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32MultiArray


class GamepadController(Node):
    def __init__(self):
        super().__init__('teleop_node')

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        # QBot LED topic (common)
        self.led_pub = self.create_publisher(Float32MultiArray, '/qbot_platform/led', 10)

        self.create_subscription(Joy, '/joy', self.joy_callback, 10)
        self.get_logger().info("teleop_node running (RB=half speed, X=kill)")

    def joy_callback(self, msg: Joy):
        twist = Twist()

        # Left stick typical mapping on Logitech F710
        linear = msg.axes[1]    # forward/back
        angular = msg.axes[0]   # turn

        # deadband
        if abs(linear) < 0.05:
            linear = 0.0
        if abs(angular) < 0.05:
            angular = 0.0

        rb = msg.buttons[5]   # RB
        x = msg.buttons[2]    # X

        # Kill signal
        if x:
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.cmd_pub.publish(twist)

            led = Float32MultiArray()
            led.data = [1.0, 0.0, 0.0]  # red on kill (optional)
            self.led_pub.publish(led)

            self.get_logger().warn("KILL pressed -> stopping + shutdown")
            rclpy.shutdown()
            return

        scale = 0.5 if rb else 1.0
        twist.linear.x = linear * scale
        twist.angular.z = angular * scale
        self.cmd_pub.publish(twist)

        # LED direction
        led = Float32MultiArray()
        if twist.linear.x > 0.05:
            led.data = [0.0, 1.0, 0.0]   # green forward
        elif twist.linear.x < -0.05:
            led.data = [0.0, 0.0, 1.0]   # blue backward
        else:
            led.data = [1.0, 1.0, 0.0]   # yellow stopped
        self.led_pub.publish(led)


def main(args=None):
    rclpy.init(args=args)
    node = GamepadController()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
