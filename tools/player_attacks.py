"""Alundra's attacks, named by the player animation that uses each balance pair.

Native routing (docs/2026-10-05-native-animation-attack-routing.txt): animation
a uses attack pair a+1 when it exists, else pair 0 (shared fallback, shown as
Contact Damage). Animation names are the pinned source's PlayerAnimation enum
(xcasadio 242b09a2, Gameplay/PlayerAnimation.cs), written as words; "Reserved"
entries have no known use. Pairs whose attribute is 0 do no damage and are
hidden in the database (their bytes are kept unchanged).
"""
import re

PLAYER_ANIMATIONS = {
    0x00:'Idle',0x01:'Moving',0x02:'StartJumpWhileMoving',0x03:'Sprint',0x04:'SprintDash',0x05:'PickupObject',
    0x06:'StartJumpWithObjectWhileMoving',0x07:'MovingWithObject',0x08:'FlailHitIron',0x09:'ThrowObject',
    0x0A:'ThrowObjectWhileJumping',0x0B:'Reserved0B',0x0C:'HoldObject',0x0D:'Sleeping',0x0E:'Climbing',0x0F:'SwimmingSlow',
    0x10:'AttackSwordDaggerLegend',0x11:'AttackWandIceChargedFireCharged',0x12:'AttackFlailIron',0x13:'AttackBowHunterWillowCharged',
    0x14:'JumpAttackSwordDagger',0x15:'JumpAttackWandIceFire',0x16:'JumpAttackFlailIron',0x17:'JumpAttackBowHunterWillow',
    0x18:'ChargeAttackSword',0x19:'ChargeAttackFlailSteel',0x1A:'InMineCart',0x1B:'InMineCartMoving',0x1C:'DamageKnockBack',
    0x1D:'SwimmingStill',0x1E:'MineCartStopping',0x1F:'Reserved1F',0x20:'EnterSand',0x21:'ExitSand',0x22:'InSand',
    0x23:'InSandMoving',0x24:'InSandDash',0x25:'FlailHitWallSteel',0x26:'Reserved26',0x27:'FlailDashHitWallSteel',
    0x28:'SwimmingDash',0x29:'PrepareSprint',0x2A:'StopSprint',0x2B:'StartJump',0x2C:'JumpMoving',0x2D:'Jump',
    0x2E:'StartJumpWithObject',0x2F:'JumpMovingWithObject',0x30:'JumpWithObject',0x31:'DamageTaken',0x32:'StartSpellCast',
    0x33:'LoopSpellCast',0x34:'EndSpellCast',0x35:'ClimbStill',0x36:'LoadingMap',0x37:'MineCartMovingFast',
    0x38:'Reserved38',0x39:'Reserved39',0x3A:'DamageTakenSwimming',0x3B:'DamageKnockBackSwimming',0x3C:'Reserved3C',
    0x3D:'Reserved3D',0x3E:'SprintAgainstWall',0x3F:'AttackSword',0x40:'AttackFlailSteel',0x41:'JumpAttackSword',
    0x42:'JumpAttackFlailSteel',0x43:'ChargedAttackFlailIron',0x44:'AttackSwordFiendBlade',0x45:'Reserved45',
    0x46:'JumpAttackSwordFiendBlade',0x47:'Reserved47',0x48:'ChargedAttackFlailShortIron',0x49:'AttackSwordHoly',
    0x4A:'Reserved4A',0x4B:'JumpAttackSwordHoly',0x4C:'Reserved4C',0x4D:'Reserved4D',0x4E:'Dead',0x4F:'Reserved4F',
    0x50:'StartPrayMourn',0x51:'PrayMourn',0x52:'StopPrayMourn',0x53:'WakingUpLaying',0x54:'AwakeLaying',
    0x55:'ShakeHeadLaying',0x56:'Reserved56',0x57:'MonsterAlundraOO',0x58:'GetThrownAway',0x59:'EndEarthquake',
    0x5A:'StartEarthquake',0x5B:'StartVictoryPose',0x5C:'VictoryPose',0x5D:'VictoryPoseShine'}


def words(name):
    text = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', ' ', name)
    return text.replace('Willow Charged', 'Willow (Charged)').replace('Ice Charged Fire Charged', 'Ice / Fire (Charged)')


def pair_label(index):
    """Label for attack pair `index` of Alundra's balance record."""
    if index == 0:
        return 'Contact Damage'
    animation = index - 1
    name = PLAYER_ANIMATIONS.get(animation)
    if not name or name.startswith('Reserved'):
        return f'Unnamed animation {animation:02X}'
    return f'{words(name)} (animation {animation:02X})'


def player_label(row, index, attack):
    """None hides a pair that does no damage (attribute 0); Contact Damage always shows."""
    if index and not attack.get('attribute'):
        return None
    return pair_label(index)
