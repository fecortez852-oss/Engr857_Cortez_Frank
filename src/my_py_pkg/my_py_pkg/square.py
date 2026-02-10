#!/usr/bin/env python3
"""
Name: Frank Cortez
Filename: square.py
Description:
  Subscribes to /numbers (std_msgs/Int32), squares the value, and prints it.
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32


class Square(Node):
    def __init__(self):
        super().__init__('square')
        self.subscription = self.create_subscription(
            Int32,
            'numbers',
            self.listener_callback,
            10
        )

    def listener_callback(self, msg: Int32):
        squared = msg.data * msg.data
        self.get_logger().info(f'square received: {msg.data} | squared: {squared}')


def main(args=None):
    rclpy.init(args=args)
    node = Square()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
