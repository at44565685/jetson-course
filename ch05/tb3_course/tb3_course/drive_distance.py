"""利用里程計精準前進固定距離。

訂閱 /odom（nav_msgs/Odometry），記下起點後持續前進，
移動距離達到 distance 時停車並結束程式。另外印出車頭方向，
示範如何把四元數（quaternion）換算成偏航角（yaw）。

參數：
  distance  前進距離（公尺），預設 1.0
  speed     前進速度（公尺／秒），預設 0.1
"""
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


def yaw_from_quaternion(q):
    """四元數 (x, y, z, w) 換算為繞 z 軸的偏航角（弧度）。"""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class DriveDistance(Node):

    def __init__(self):
        super().__init__('drive_distance')
        self.declare_parameter('distance', 1.0)
        self.declare_parameter('speed', 0.1)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.odom_sub = self.create_subscription(Odometry, '/odom', self.on_odom, 10)
        self.start = None
        self.done = False

    def on_odom(self, msg):
        if self.done:
            return
        p = msg.pose.pose.position
        if self.start is None:
            self.start = (p.x, p.y)
            yaw = math.degrees(yaw_from_quaternion(msg.pose.pose.orientation))
            self.get_logger().info(
                f'起點 x={p.x:.2f} y={p.y:.2f}，車頭方向 {yaw:.1f}°')

        travelled = math.hypot(p.x - self.start[0], p.y - self.start[1])
        target = self.get_parameter('distance').value

        cmd = Twist()
        if travelled < target:
            cmd.linear.x = float(self.get_parameter('speed').value)
            self.cmd_pub.publish(cmd)
        else:
            self.cmd_pub.publish(cmd)   # 全為 0 的 Twist 即停車
            self.get_logger().info(f'已前進 {travelled:.3f} m（目標 {target} m），停車')
            self.done = True


def main():
    rclpy.init()
    node = DriveDistance()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd_pub.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
