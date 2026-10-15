"""以程式送出導航目標，讓 TurtleBot3 依序巡邏在 RViz 上點選的位置。

使用 nav2_simple_commander（Nav2 的 Python 介面），底層為 ROS 2 的動作（action）：
送出目標（goal）後持續收到回饋（feedback），最後取得結果（result）。

操作步驟：
  1. 啟動 turtlebot3_fortress 模擬與 Nav2（載入已建立的地圖）
  2. 在 RViz 以「2D Pose Estimate」標出車子目前的位置，確認光達紅點與地圖的牆對齊
  3. 執行本程式：
       ros2 run tb3_course patrol --ros-args -p use_sim_time:=true
  4. 在 RViz 以「Publish Point」在地圖上依序點選巡邏點（預設 3 個）
     點選的座標會發布到 /clicked_point（geometry_msgs/msg/PointStamped）

參數：
  num_points  巡邏點數量，預設 3
  loops       巡邏圈數，預設 1
"""
import math

import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult


def make_pose(navigator, x, y, yaw):
    pose = PoseStamped()
    pose.header.frame_id = 'map'
    pose.header.stamp = navigator.get_clock().now().to_msg()
    pose.pose.position.x = x
    pose.pose.position.y = y
    pose.pose.orientation.z = math.sin(yaw / 2.0)
    pose.pose.orientation.w = math.cos(yaw / 2.0)
    return pose


def main():
    rclpy.init()
    navigator = BasicNavigator()
    navigator.declare_parameter('num_points', 3)
    navigator.declare_parameter('loops', 1)
    num_points = navigator.get_parameter('num_points').value
    loops = navigator.get_parameter('loops').value

    # 1. 等待 Nav2 啟動。初始位置由使用者在 RViz 以 2D Pose Estimate 設定，
    #    因此不使用 BasicNavigator 預設的「自動發布初始位置 (0, 0)」。
    navigator.waitUntilNav2Active(localizer='controller_server')
    while not navigator.initial_pose_received:      # 收到 AMCL 的 /amcl_pose 後變為 True
        navigator.info('等待初始位置：請在 RViz 以 2D Pose Estimate 標出車子的位置')
        rclpy.spin_once(navigator, timeout_sec=3.0)

    # 2. 收集巡邏點：訂閱 RViz「Publish Point」發布的 /clicked_point
    points = []

    def on_click(msg):
        if len(points) < num_points:
            points.append((msg.point.x, msg.point.y))
            navigator.info(f'第 {len(points)} 點：x={msg.point.x:.2f}, y={msg.point.y:.2f}')

    navigator.create_subscription(PointStamped, '/clicked_point', on_click, 10)
    navigator.info(f'請在 RViz 以 Publish Point 依序點選 {num_points} 個巡邏點')
    while len(points) < num_points:
        rclpy.spin_once(navigator, timeout_sec=0.5)

    # 3. 依序前往各點；車頭方向朝向下一個點
    for lap in range(1, loops + 1):
        for i, (x, y) in enumerate(points):
            nx, ny = points[(i + 1) % len(points)]
            yaw = math.atan2(ny - y, nx - x)
            navigator.info(f'第 {lap} 圈，前往第 {i + 1} 點 ({x:.2f}, {y:.2f})')
            navigator.goToPose(make_pose(navigator, x, y, yaw))

            while not navigator.isTaskComplete():
                feedback = navigator.getFeedback()
                if feedback:
                    navigator.get_logger().info(
                        f'  剩餘距離 {feedback.distance_remaining:.2f} m',
                        throttle_duration_sec=2.0)

            result = navigator.getResult()
            if result != TaskResult.SUCCEEDED:
                navigator.warn(f'第 {i + 1} 點未到達（{result}），結束巡邏')
                rclpy.shutdown()
                return
            navigator.info(f'第 {i + 1} 點到達')

    navigator.info('巡邏結束')
    rclpy.shutdown()


if __name__ == '__main__':
    main()
