import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import {
  Settings,
  Award,
  Target,
  Share,
  Bell,
  MapPin,
  Calendar,
  Trophy,
  Heart,
  Leaf,
  ChevronRight,
  LogOut
} from 'lucide-react-native';
import { useAuth } from '@/contexts/AuthContext';
import { router } from 'expo-router';

export default function ProfileScreen() {
  const { user, profile, signOut } = useAuth();

  const achievements = [
    { id: 1, title: '첫 플로깅', description: '첫 번째 플로깅을 완료했습니다', icon: '🏃‍♂️', unlocked: true },
    { id: 2, title: '환경 수호자', description: '100개 쓰레기 수집', icon: '🌍', unlocked: true },
    { id: 3, title: '지구 지킴이', description: '500개 쓰레기 수집', icon: '🌱', unlocked: false },
    { id: 4, title: '마라톤 러너', description: '42km 누적 달리기', icon: '🏃‍♀️', unlocked: true },
    { id: 5, title: '일주일 챌린지', description: '7일 연속 플로깅', icon: '🔥', unlocked: false },
    { id: 6, title: '킬로미터 킹', description: '100km 누적 달리기', icon: '👑', unlocked: false },
  ];

  const menuItems = [
    {
      icon: Target,
      title: '목표 설정',
      subtitle: '개인 플로깅 목표를 설정하세요',
      color: '#10B981'
    },
    {
      icon: Bell,
      title: '알림 설정',
      subtitle: '운동 리마인더 및 알림 설정',
      color: '#3B82F6'
    },
    {
      icon: Share,
      title: '친구 초대',
      subtitle: '친구와 함께 플로깅하세요',
      color: '#8B5CF6'
    },
    {
      icon: Settings,
      title: '설정',
      subtitle: '앱 설정 및 개인정보 관리',
      color: '#6B7280'
    },
  ];

  const handleSignOut = async () => {
    await signOut();
    router.replace('/auth');
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <LinearGradient
          colors={['#10B981', '#059669']}
          style={styles.profileHeader}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
        >
          <View style={styles.profileInfo}>
            <View style={styles.avatarContainer}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>{profile?.username?.[0]?.toUpperCase() || '플'}</Text>
              </View>
            </View>
            <Text style={styles.profileName}>{profile?.full_name || profile?.username || '플로거님'}</Text>
            <Text style={styles.profileEmail}>{user?.email}</Text>
            <View style={styles.levelContainer}>
              <Trophy size={16} color="#ffffff" />
              <Text style={styles.levelText}>레벨 {profile?.level || 1} • 지구 지킴이</Text>
            </View>
          </View>
        </LinearGradient>

        <View style={styles.quickStatsContainer}>
          <View style={styles.quickStatsCard}>
            <View style={styles.quickStat}>
              <MapPin size={20} color="#10B981" />
              <Text style={styles.quickStatValue}>{Number(profile?.total_distance || 0).toFixed(1)}km</Text>
              <Text style={styles.quickStatLabel}>총 거리</Text>
            </View>
            <View style={styles.quickStatDivider} />
            <View style={styles.quickStat}>
              <Leaf size={20} color="#10B981" />
              <Text style={styles.quickStatValue}>{profile?.total_trash_collected || 0}</Text>
              <Text style={styles.quickStatLabel}>쓰레기 수집</Text>
            </View>
            <View style={styles.quickStatDivider} />
            <View style={styles.quickStat}>
              <Calendar size={20} color="#10B981" />
              <Text style={styles.quickStatValue}>{profile?.total_sessions || 0}</Text>
              <Text style={styles.quickStatLabel}>플로깅 횟수</Text>
            </View>
          </View>
        </View>

        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>성과</Text>
            <TouchableOpacity style={styles.seeAllButton}>
              <Text style={styles.seeAllText}>모두 보기</Text>
              <ChevronRight size={16} color="#10B981" />
            </TouchableOpacity>
          </View>

          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.achievementsContainer}
          >
            {achievements.map((achievement) => (
              <View
                key={achievement.id}
                style={[
                  styles.achievementCard,
                  !achievement.unlocked && styles.achievementCardLocked
                ]}
              >
                <Text style={styles.achievementIcon}>{achievement.icon}</Text>
                <Text style={[
                  styles.achievementTitle,
                  !achievement.unlocked && styles.achievementTitleLocked
                ]}>
                  {achievement.title}
                </Text>
                <Text style={[
                  styles.achievementDescription,
                  !achievement.unlocked && styles.achievementDescriptionLocked
                ]}>
                  {achievement.description}
                </Text>
                {achievement.unlocked && (
                  <View style={styles.unlockedBadge}>
                    <Award size={12} color="#10B981" />
                  </View>
                )}
              </View>
            ))}
          </ScrollView>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>이번 주 목표</Text>
          <View style={styles.goalCard}>
            <View style={styles.goalHeader}>
              <View>
                <Text style={styles.goalTitle}>20km 플로깅 & 쓰레기 50개 수집</Text>
                <Text style={styles.goalProgress}>12.5km 완료 • 28개 수집</Text>
              </View>
              <Text style={styles.goalPercentage}>62%</Text>
            </View>
            <View style={styles.progressBarContainer}>
              <View style={styles.progressBar}>
                <View style={[styles.progressFill, { width: '62%' }]} />
              </View>
            </View>
            <View style={styles.goalDetails}>
              <View style={styles.goalDetail}>
                <MapPin size={14} color="#6B7280" />
                <Text style={styles.goalDetailText}>7.5km 남음</Text>
              </View>
              <View style={styles.goalDetail}>
                <Leaf size={14} color="#6B7280" />
                <Text style={styles.goalDetailText}>22개 남음</Text>
              </View>
            </View>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>메뉴</Text>
          <View style={styles.menuContainer}>
            {menuItems.map((item, index) => (
              <TouchableOpacity key={index} style={styles.menuItem}>
                <View style={styles.menuItemLeft}>
                  <View style={[styles.menuItemIcon, { backgroundColor: `${item.color}15` }]}>
                    <item.icon size={20} color={item.color} />
                  </View>
                  <View style={styles.menuItemText}>
                    <Text style={styles.menuItemTitle}>{item.title}</Text>
                    <Text style={styles.menuItemSubtitle}>{item.subtitle}</Text>
                  </View>
                </View>
                <ChevronRight size={20} color="#9CA3AF" />
              </TouchableOpacity>
            ))}
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>환경 기여도</Text>
          <View style={styles.impactCard}>
            <LinearGradient
              colors={['#34D399', '#10B981']}
              style={styles.impactGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            >
              <View style={styles.impactContent}>
                <Heart size={24} color="#ffffff" />
                <View style={styles.impactText}>
                  <Text style={styles.impactTitle}>올해의 환경 기여</Text>
                  <Text style={styles.impactValue}>{((profile?.total_trash_collected || 0) * 0.035).toFixed(1)}kg CO₂ 절약</Text>
                  <Text style={styles.impactDescription}>
                    {profile?.total_trash_collected || 0}개의 쓰레기를 수집하여 환경을 보호했습니다
                  </Text>
                </View>
              </View>
            </LinearGradient>
          </View>
        </View>

        {/* 로그아웃 버튼 섹션 */}
        <View style={styles.section}>
          <TouchableOpacity style={styles.logoutButton} onPress={handleSignOut}>
            <View style={styles.logoutButtonContent}>
              <LogOut size={20} color="#EF4444" />
              <Text style={styles.logoutButtonText}>로그아웃</Text>
            </View>
          </TouchableOpacity>
        </View>

        {/* 하단 여백 */}
        <View style={styles.bottomSpacer} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  profileHeader: {
    paddingTop: 20,
    paddingBottom: 40,
    paddingHorizontal: 20,
  },
  profileInfo: {
    alignItems: 'center',
  },
  avatarContainer: {
    marginBottom: 16,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 3,
    borderColor: 'rgba(255, 255, 255, 0.3)',
  },
  avatarText: {
    fontSize: 28,
    fontWeight: '800',
    color: '#ffffff',
  },
  profileName: {
    fontSize: 24,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 4,
  },
  profileEmail: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginBottom: 12,
  },
  levelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    gap: 6,
  },
  levelText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#ffffff',
  },
  quickStatsContainer: {
    marginTop: -20,
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  quickStatsCard: {
    backgroundColor: '#ffffff',
    flexDirection: 'row',
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 6,
  },
  quickStat: {
    flex: 1,
    alignItems: 'center',
    gap: 8,
  },
  quickStatDivider: {
    width: 1,
    backgroundColor: '#E5E7EB',
    marginHorizontal: 16,
  },
  quickStatValue: {
    fontSize: 20,
    fontWeight: '800',
    color: '#1F2937',
  },
  quickStatLabel: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  section: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1F2937',
  },
  seeAllButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  seeAllText: {
    fontSize: 14,
    color: '#10B981',
    fontWeight: '600',
  },
  achievementsContainer: {
    paddingRight: 20,
  },
  achievementCard: {
    width: 140,
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 12,
    marginRight: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
    position: 'relative',
  },
  achievementCardLocked: {
    opacity: 0.5,
  },
  achievementIcon: {
    fontSize: 24,
    marginBottom: 8,
  },
  achievementTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
    textAlign: 'center',
    marginBottom: 4,
  },
  achievementTitleLocked: {
    color: '#9CA3AF',
  },
  achievementDescription: {
    fontSize: 12,
    color: '#6B7280',
    textAlign: 'center',
    lineHeight: 16,
  },
  achievementDescriptionLocked: {
    color: '#D1D5DB',
  },
  unlockedBadge: {
    position: 'absolute',
    top: 8,
    right: 8,
    backgroundColor: '#ECFDF5',
    borderRadius: 10,
    padding: 4,
  },
  goalCard: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  goalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  goalTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
    flex: 1,
  },
  goalProgress: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  goalPercentage: {
    fontSize: 20,
    fontWeight: '800',
    color: '#10B981',
  },
  progressBarContainer: {
    marginBottom: 12,
  },
  progressBar: {
    height: 6,
    backgroundColor: '#E5E7EB',
    borderRadius: 3,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#10B981',
    borderRadius: 3,
  },
  goalDetails: {
    flexDirection: 'row',
    gap: 16,
  },
  goalDetail: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  goalDetailText: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  menuContainer: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  menuItemLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  menuItemIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  menuItemText: {
    flex: 1,
  },
  menuItemTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
  },
  menuItemSubtitle: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 2,
  },
  impactCard: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  impactGradient: {
    padding: 20,
  },
  impactContent: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 16,
  },
  impactText: {
    flex: 1,
  },
  impactTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 8,
  },
  impactValue: {
    fontSize: 24,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 8,
  },
  impactDescription: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.9)',
    lineHeight: 20,
  },
  logoutButton: {
    backgroundColor: '#ffffff',
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
    borderWidth: 1,
    borderColor: '#FEE2E2',
  },
  logoutButtonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
    gap: 12,
  },
  logoutButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#EF4444',
  },
  bottomSpacer: {
    height: 40,
  },
});