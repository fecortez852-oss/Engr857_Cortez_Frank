#!/usr/bin/env python3
"""
Name: Frank Cortez
Filename: num_talker.py
Description:
  ROS2 node that publishes random integers to the /numbers topic using std_msgs/Int32.
"""

import random

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class NumTalker(Node):
    """Publishes random integers on /numbers once per second."""

    def __init__(self):
        super().__init__('num_talker')
        self.publisher_ = self.create_publisher(Int32, 'numbers', 10)
        self.timer = self.create_timer(1.0, self.publish_number)

    def publish_number(self):
        msg = Int32()
        msg.data = random.randint(0, 20)
        self.publisher_.publish(msg)
        self.get_logger().info(f'num_talker published: {msg.data}')


def main(args=None):
    rclpy.init(args=args)
    node = NumTalker()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
