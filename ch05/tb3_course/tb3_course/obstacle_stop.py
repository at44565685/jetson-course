"""第一個閉迴路控制節點：前方有障礙物就停車。

訂閱 /scan（sensor_msgs/LaserScan），發布 /cmd_vel（geometry_msgs/Twist）。
車子以固定速度前進；正前方 ±front_angle 度內的最近距離小於 stop_distance 時停車。

參數（可用 ros2 param set 即時修改）：
  stop_distance  停車距離（公尺），預設 0.4
  forward_speed  前進速度（公尺／秒），預設 0.15
  front_angle    偵測範圍（度，左右各半），預設 15
"""
import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan


class ObstacleStop(Node):

    def __init__(self):
        super().__init__('obstacle_stop')
        self.declare_parameter('stop_distance', 0.4)
        self.declare_parameter('forward_speed', 0.15)
        self.declare_parameter('front_angle', 15)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.on_scan, qos_profile_sensor_data)
        self.was_blocked = None
        self.get_logger().info('obstacle_stop 已啟動，等待 /scan ...')

    def front_min_distance(self, scan):
        """回傳正前方 ±front_angle 度內的最近有效距離。"""
        half = math.radians(self.get_parameter('front_angle').value)
        nearest = math.inf
        for i, r in enumerate(scan.ranges):
            # 將角度換算到 -pi ~ pi，0 為車頭正前方
            angle = scan.angle_min + i * scan.angle_increment
            angle = math.atan2(math.sin(angle), math.cos(angle))
            if abs(angle) > half:
                continue
            if scan.range_min < r < scan.range_max:   # 排除 inf、nan 與量測範圍外的值
                nearest = min(nearest, r)
        return nearest

    def on_scan(self, scan):
        stop_distance = self.get_parameter('stop_distance').value
        distance = self.front_min_distance(scan)
        blocked = distance < stop_distance

        cmd = Twist()
        if not blocked:
            cmd.linear.x = float(self.get_parameter('forward_speed').value)
        self.cmd_pub.publish(cmd)

        if blocked != self.was_blocked:   # 狀態改變時才印訊息，避免洗版
            state = '停車' if blocked else '前進'
            self.get_logger().info(f'{state}：前方最近距離 {distance:.2f} m')
            self.was_blocked = blocked

    def stop(self):
        self.cmd_pub.publish(Twist())


def main():
    rclpy.init()
    node = ObstacleStop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
