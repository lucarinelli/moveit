#!/usr/bin/env python
import time

import pytest
import rospy
from geometry_msgs.msg import TwistStamped

from control_msgs.msg import JointJog
from trajectory_msgs.msg import JointTrajectory

# This can be run as part of a pytest, or like a normal ROS executable:
# rosrun moveit_jog_arm test_jog_arm_integration.py

JOG_ARM_SETTLE_TIME_S = 3
ROS_SETTLE_TIME_S = 3

JOINT_JOG_COMMAND_TOPIC = 'jog_server/joint_delta_jog_cmds'
CARTESIAN_JOG_COMMAND_TOPIC = 'jog_server/delta_jog_cmds'

COMMAND_OUT_TOPIC = 'jog_server/command'


@pytest.fixture
def node():
    return rospy.init_node('pytest', anonymous=True)


class JointJogCmd(object):
    def __init__(self):
        self._pub = rospy.Publisher(JOINT_JOG_COMMAND_TOPIC, JointJog, queue_size=1)

    def send_joint_velocity_cmd(self, joint_pos):
        jj = JointJog()
        jj.header.stamp = rospy.Time.now()
        jj.joint_names = ['joint_{}'.format(i) for i in range(len(joint_pos))]
        jj.velocities = list(map(float, joint_pos))
        self._pub.publish(jj)


class CartesianJogCmd(object):
    def __init__(self):
        self._pub = rospy.Publisher(
            CARTESIAN_JOG_COMMAND_TOPIC, TwistStamped, queue_size=1
        )

    def send_cmd(self, linear, angular):
        ts = TwistStamped()
        ts.header.stamp = rospy.Time.now()
        ts.twist.linear.x, ts.twist.linear.y, ts.twist.linear.z = linear
        ts.twist.angular.x, ts.twist.angular.y, ts.twist.angular.z = angular
        self._pub.publish(ts)


def test_jog_arm_trajectory_generated_when_jog_command_is_received(node):
    sub = rospy.Subscriber(
        COMMAND_OUT_TOPIC, JointTrajectory, lambda msg: received.append(msg)
    )
    cartesian_cmd = CartesianJogCmd()
    time.sleep(ROS_SETTLE_TIME_S)  # wait for pub/subs to settle
    time.sleep(JOG_ARM_SETTLE_TIME_S)  # wait for jog_arm server to init

    # Repeated zero-commands should produce no output, other than a few halt messages
    # A subscriber in a different thread fills 'received'
    cartesian_cmd.send_cmd([0, 0, 0], [0, 0, 0])
    cartesian_cmd.send_cmd([0, 0, 0], [0, 0, 0])
    cartesian_cmd.send_cmd([0, 0, 0], [0, 0, 0])
    cartesian_cmd.send_cmd([0, 0, 0], [0, 0, 0])
    received = []
    rospy.sleep(1)
    assert len(received) <= 2 # 2 is 'num_outgoing_halt_msgs_to_publish' in the config file

    # This nonzero command should produce jogging output
    # A subscriber in a different thread fills `received`
    TEST_DURATION = 1
    PUBLISH_PERIOD = 0.01 # 'PUBLISH_PERIOD' from config file
    cartesian_cmd.send_cmd([0, 0, 0], [0, 0, 1])
    received = []
    rospy.sleep(TEST_DURATION)
    # TEST_DURATION/PUBLISH_PERIOD is the expected number of messages in this duration.
    # Allow a small +/- window due to rounding/timing errors
    assert len(received) >= TEST_DURATION/PUBLISH_PERIOD - 5
    assert len(received) <= TEST_DURATION/PUBLISH_PERIOD + 5


def test_jog_arm_joint_command(node):
    # Test sending a joint command

    sub = rospy.Subscriber(
        COMMAND_OUT_TOPIC, JointTrajectory, lambda msg: received.append(msg)
    )

    joint_cmd = JointJogCmd()
    time.sleep(ROS_SETTLE_TIME_S)  # wait for pub/subs to settle
    time.sleep(JOG_ARM_SETTLE_TIME_S)  # wait for jog_arm server to init

    received = []
    TEST_DURATION = 1
    PUBLISH_PERIOD = 0.01 # 'PUBLISH_PERIOD' from config file
    JOINT_VELOCITY_LIMIT = 1
    velocities = [0.1]
    joint_cmd.send_joint_velocity_cmd(velocities)
    rospy.sleep(TEST_DURATION)
    # TEST_DURATION/PUBLISH_PERIOD is the expected number of messages in this duration.
    # Allow a small +/- window due to rounding/timing errors
    assert len(received) >= TEST_DURATION/PUBLISH_PERIOD - 5
    assert len(received) <= TEST_DURATION/PUBLISH_PERIOD + 5


if __name__ == '__main__':
   node = node()
   test_jog_arm_trajectory_generated_when_jog_command_is_received(node)
   test_jog_arm_joint_command(node)
