import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Dimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Play, Award, Trash2, MapPin, Target, TrendingUp } from 'lucide-react-native';

const { width } = Dimensions.get('window');

export default function HomeScreen() {
  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.greeting}>안녕하세요!</Text>
          <Text style={styles.username}>플로거님</Text>
        </View>

        {/* Quick Stats */}
        <View style={styles.statsContainer}>
          <LinearGradient
            colors={['#10B981', '#059669']}
            style={styles.mainCard}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
          >
            <View style={styles.mainCardContent}>
              <View>
                <Text style={styles.mainCardTitle}>이번 주 플로깅</Text>
                <Text style={styles.mainCardValue}>12.5km</Text>
                <Text style={styles.mainCardSubtitle}>쓰레기 45개 수집</Text>
              </View>
              <Award size={48} color="#ffffff" />
            </View>
          </LinearGradient>
        </View>

        {/* Stats Grid */}
        <View style={styles.gridContainer}>
          <View style={styles.statCard}>
            <Trash2 size={24} color="#10B981" />
            <Text style={styles.statValue}>245</Text>
            <Text style={styles.statLabel}>총 쓰레기</Text>
          </View>
          <View style={styles.statCard}>
            <MapPin size={24} color="#10B981" />
            <Text style={styles.statValue}>87.2km</Text>
            <Text style={styles.statLabel}>총 거리</Text>
          </View>
          <View style={styles.statCard}>
            <Target size={24} color="#10B981" />
            <Text style={styles.statValue}>24</Text>
            <Text style={styles.statLabel}>플로깅 횟수</Text>
          </View>
          <View style={styles.statCard}>
            <TrendingUp size={24} color="#10B981" />
            <Text style={styles.statValue}>레벨 7</Text>
            <Text style={styles.statLabel}>현재 레벨</Text>
          </View>
        </View>

        {/* Quick Actions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>빠른 시작</Text>
          <TouchableOpacity style={styles.actionButton}>
            <LinearGradient
              colors={['#10B981', '#059669']}
              style={styles.actionButtonGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
            >
              <Play size={24} color="#ffffff" />
              <Text style={styles.actionButtonText}>플로깅 시작하기</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>

        {/* Today's Goal */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>오늘의 목표</Text>
          <View style={styles.goalCard}>
            <View style={styles.goalHeader}>
              <Text style={styles.goalTitle}>5km 플로깅 & 쓰레기 20개 수집</Text>
              <Text style={styles.goalProgress}>60%</Text>
            </View>
            <View style={styles.progressBar}>
              <View style={[styles.progressFill, { width: '60%' }]} />
            </View>
            <Text style={styles.goalDescription}>3km 완료, 쓰레기 12개 수집</Text>
          </View>
        </View>

        {/* Recent Activity */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>최근 활동</Text>
          <View style={styles.activityCard}>
            <View style={styles.activityHeader}>
              <View>
                <Text style={styles.activityTitle}>한강공원 플로깅</Text>
                <Text style={styles.activityDate}>2025년 1월 15일</Text>
              </View>
              <Text style={styles.activityDistance}>3.2km</Text>
            </View>
            <View style={styles.activityStats}>
              <View style={styles.activityStat}>
                <Text style={styles.activityStatValue}>28</Text>
                <Text style={styles.activityStatLabel}>쓰레기</Text>
              </View>
              <View style={styles.activityStat}>
                <Text style={styles.activityStatValue}>25'</Text>
                <Text style={styles.activityStatLabel}>시간</Text>
              </View>
              <View style={styles.activityStat}>
                <Text style={styles.activityStatValue}>180</Text>
                <Text style={styles.activityStatLabel}>칼로리</Text>
              </View>
            </View>
          </View>
        </View>

        {/* Environmental Impact */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>환경 기여도</Text>
          <View style={styles.impactCard}>
            <LinearGradient
              colors={['#34D399', '#10B981']}
              style={styles.impactGradient}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
            >
              <Text style={styles.impactTitle}>이번 달 환경 보호</Text>
              <Text style={styles.impactValue}>2.4kg</Text>
              <Text style={styles.impactSubtitle}>쓰레기 제거량</Text>
              <Text style={styles.impactDescription}>
                🌱 탄소발자국 3.2kg 감소 효과
              </Text>
            </LinearGradient>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  header: {
    padding: 20,
    paddingTop: 10,
  },
  greeting: {
    fontSize: 16,
    color: '#6B7280',
    fontWeight: '500',
  },
  username: {
    fontSize: 28,
    fontWeight: '800',
    color: '#1F2937',
    marginTop: 4,
  },
  statsContainer: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  mainCard: {
    borderRadius: 16,
    padding: 20,
  },
  mainCardContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  mainCardTitle: {
    fontSize: 16,
    color: '#ffffff',
    opacity: 0.9,
    fontWeight: '500',
  },
  mainCardValue: {
    fontSize: 32,
    color: '#ffffff',
    fontWeight: '800',
    marginTop: 4,
  },
  mainCardSubtitle: {
    fontSize: 14,
    color: '#ffffff',
    opacity: 0.8,
    marginTop: 4,
  },
  gridContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 20,
    marginBottom: 20,
    gap: 12,
  },
  statCard: {
    backgroundColor: '#ffffff',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    width: (width - 56) / 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  statValue: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1F2937',
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
    fontWeight: '500',
  },
  section: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 16,
  },
  actionButton: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  actionButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    gap: 12,
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },
  goalCard: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 12,
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
    fontSize: 18,
    fontWeight: '700',
    color: '#10B981',
  },
  progressBar: {
    height: 6,
    backgroundColor: '#E5E7EB',
    borderRadius: 3,
    marginBottom: 8,
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#10B981',
    borderRadius: 3,
  },
  goalDescription: {
    fontSize: 14,
    color: '#6B7280',
  },
  activityCard: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  activityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  activityTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
  },
  activityDate: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
  activityDistance: {
    fontSize: 20,
    fontWeight: '700',
    color: '#10B981',
  },
  activityStats: {
    flexDirection: 'row',
    gap: 24,
  },
  activityStat: {
    alignItems: 'center',
  },
  activityStatValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1F2937',
  },
  activityStatLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
  },
  impactCard: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  impactGradient: {
    padding: 20,
  },
  impactTitle: {
    fontSize: 16,
    color: '#ffffff',
    fontWeight: '500',
    opacity: 0.9,
  },
  impactValue: {
    fontSize: 32,
    color: '#ffffff',
    fontWeight: '800',
    marginTop: 8,
  },
  impactSubtitle: {
    fontSize: 14,
    color: '#ffffff',
    opacity: 0.8,
    marginTop: 4,
  },
  impactDescription: {
    fontSize: 14,
    color: '#ffffff',
    marginTop: 12,
    opacity: 0.9,
  },
});