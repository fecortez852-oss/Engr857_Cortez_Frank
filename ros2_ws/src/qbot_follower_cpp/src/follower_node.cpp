#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/laser_scan.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "std_msgs/msg/float32_multi_array.hpp"

class QBotFollower : public rclcpp::Node
{
public:
  QBotFollower() : Node("qbot_follower_cpp")
  {
    scan_topic_ = this->declare_parameter<std::string>("scan_topic", "/scan");
    cmd_vel_topic_ = this->declare_parameter<std::string>("cmd_vel_topic", "/cmd_vel");

    // LED debug
    led_topic_ = this->declare_parameter<std::string>("led_topic", "/cmd_led");
    publish_led_ = this->declare_parameter<bool>("publish_led", true);

    // Distances
    target_distance_  = this->declare_parameter<double>("target_distance", 1.0);
    follow_distance_ = this->declare_parameter<double>("follow_distance", 1.5);
    pushback_distance_ = this->declare_parameter<double>("pushback_distance", 0.5);
    max_detect_distance_ = this->declare_parameter<double>("max_detect_distance", 2.0);

    // Front window settings
    front_half_angle_deg_ = this->declare_parameter<double>("front_half_angle_deg", 45.0);
    front_center_deg_     = this->declare_parameter<double>("front_center_deg", -90.0);

    // Gains / limits
    kp_lin_ = this->declare_parameter<double>("kp_lin", 0.9);
    kp_ang_ = this->declare_parameter<double>("kp_ang", 2.0);

    invert_angular_ = this->declare_parameter<bool>("invert_angular", false);

    max_lin_ = this->declare_parameter<double>("max_lin_speed", 0.30);
    max_ang_ = this->declare_parameter<double>("max_ang_speed", 1.2);
    max_rev_ = this->declare_parameter<double>("max_rev_speed", 0.20);

    deadband_ = this->declare_parameter<double>("deadband", 0.05);

    cmd_pub_ = this->create_publisher<geometry_msgs::msg::Twist>(cmd_vel_topic_, 10);

    if (publish_led_) {
      led_pub_ = this->create_publisher<std_msgs::msg::Float32MultiArray>(led_topic_, 10);
    }

    scan_sub_ = this->create_subscription<sensor_msgs::msg::LaserScan>(
      scan_topic_, rclcpp::SensorDataQoS(),
      std::bind(&QBotFollower::onScan, this, std::placeholders::_1));

    RCLCPP_INFO(this->get_logger(),
  "Follower started. target=%.2f follow=%.2f pushback=%.2f max_detect=%.2f max_rev=%.2f max_lin=%.2f front=+/-%.1fdeg center=%.1fdeg invert_ang=%s led_topic=%s",
  target_distance_, follow_distance_, pushback_distance_, max_detect_distance_,
  max_rev_, max_lin_,
  front_half_angle_deg_, front_center_deg_,
  invert_angular_ ? "true" : "false",
  led_topic_.c_str());
  }

private:
  static double clamp(double x, double lo, double hi)
  {
    return std::max(lo, std::min(hi, x));
  }

  static double wrapToPi(double a)
  {
    while (a > M_PI) a -= 2.0 * M_PI;
    while (a < -M_PI) a += 2.0 * M_PI;
    return a;
  }

  void setLED(float r, float g, float b)
  {
    if (!publish_led_ || !led_pub_) return;
    std_msgs::msg::Float32MultiArray msg;
    msg.data = {r, g, b};   // [R,G,B] in 0..1
    led_pub_->publish(msg);
  }

  void publishStop()
  {
    geometry_msgs::msg::Twist t;
    t.linear.x = 0.0;
    t.angular.z = 0.0;
    cmd_pub_->publish(t);

    // Yellow when stopped
    setLED(1.0f, 1.0f, 0.0f);
  }

  void onScan(const sensor_msgs::msg::LaserScan::SharedPtr msg)
  {
    if (!msg || msg->ranges.empty()) {
      publishStop();
      return;
    }

    const double half = front_half_angle_deg_ * M_PI / 180.0;
    const double center = front_center_deg_ * M_PI / 180.0;

    // Weighted average angle (more stable than "closest point")
    double sum_w = 0.0;
    double sum_ang = 0.0;
    double min_r = std::numeric_limits<double>::infinity();
    bool found = false;

    for (size_t i = 0; i < msg->ranges.size(); ++i) {
      const float r = msg->ranges[i];

      if (r <= 0.0f) continue; // ignore 0.0 returns
      if (std::isnan(r) || std::isinf(r)) continue;
      if (r < msg->range_min || r > msg->range_max) continue;
      if (r > max_detect_distance_) continue;

      const double angle_raw = msg->angle_min + static_cast<double>(i) * msg->angle_increment;
      const double angle_wrapped = wrapToPi(angle_raw);

      const double angle_rel = wrapToPi(angle_wrapped - center);

      if (std::fabs(angle_rel) > half) continue;

      const double w = 1.0 / std::max(0.05, static_cast<double>(r));
      sum_w += w;
      sum_ang += w * angle_rel;

      if (r < min_r) min_r = r;
      found = true;
    }

    if (!found || !std::isfinite(min_r) || sum_w <= 0.0) {
      publishStop();
      return;
    }

    const double target_angle = sum_ang / sum_w;

// ---- Distance control  ----
double lin_cmd = 0.0;

if (min_r > follow_distance_ + deadband_) {
  lin_cmd = kp_lin_ * (min_r - target_distance_);
}
else if (min_r < pushback_distance_ - deadband_) 
{
  lin_cmd = kp_lin_ * (min_r - target_distance_); }
else {
  lin_cmd = 0.4 * kp_lin_ * (min_r - target_distance_);
}
lin_cmd = clamp(lin_cmd, -max_rev_, max_lin_);

    // ---- Angle control ----
    double ang_cmd = kp_ang_ * target_angle;
    if (invert_angular_) ang_cmd = -ang_cmd;

    // Clamp 
   lin_cmd = clamp(lin_cmd, -max_rev_, max_lin_);
   ang_cmd = clamp(ang_cmd, -max_ang_, max_ang_);

    geometry_msgs::msg::Twist t;
    t.linear.x = lin_cmd;
    t.angular.z = ang_cmd;
    cmd_pub_->publish(t);

    // BLUE when detecting AND moving forward
    if (lin_cmd > 0.01) {
      setLED(0.0f, 0.0f, 1.0f);
    } else {
      // Yellow when stopped (at 1m)
      setLED(1.0f, 1.0f, 0.0f);
    }
  }

  // Params
  std::string scan_topic_;
  std::string cmd_vel_topic_;
  std::string led_topic_;
  bool publish_led_;

 double target_distance_;
double follow_distance_;
double pushback_distance_;
double max_detect_distance_;

double max_rev_;

  double front_half_angle_deg_;
  double front_center_deg_;

  double kp_lin_;
  double kp_ang_;
  bool invert_angular_;

  double max_lin_;
  double max_ang_;
  double deadband_;

  // ROS interfaces
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_pub_;
  rclcpp::Publisher<std_msgs::msg::Float32MultiArray>::SharedPtr led_pub_;
  rclcpp::Subscription<sensor_msgs::msg::LaserScan>::SharedPtr scan_sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<QBotFollower>());
  rclcpp::shutdown();
  return 0;
}