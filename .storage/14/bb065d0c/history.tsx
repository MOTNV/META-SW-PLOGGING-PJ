import React, { useState } from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Calendar, MapPin, Clock, Trash2, Zap, TrendingUp, Award } from 'lucide-react-native';

export default function HistoryScreen() {
  const [selectedPeriod, setSelectedPeriod] = useState('week');

  const periods = [
    { key: 'week', label: '이번 주' },
    { key: 'month', label: '이번 달' },
    { key: 'year', label: '올해' },
  ];

  const activities = [
    {
      id: 1,
      title: '한강공원 플로깅',
      date: '2025-01-15',
      time: '18:30',
      distance: '3.2km',
      duration: '25분',
      trash: 28,
      calories: 180,
      route: '한강공원 → 반포대교 → 한강공원',
    },
    {
      id: 2,
      title: '남산 둘레길 플로깅',
      date: '2025-01-13',
      time: '07:00',
      distance: '4.8km',
      duration: '38분',
      trash: 35,
      calories: 285,
      route: '남산 둘레길 전구간',
    },
    {
      id: 3,
      title: '올림픽공원 플로깅',
      date: '2025-01-10',
      time: '16:45',
      distance: '2.7km',
      duration: '22분',
      trash: 19,
      calories: 150,
      route: '올림픽공원 → 몽촌토성 → 올림픽공원',
    },
    {
      id: 4,
      title: '청계천 플로깅',
      date: '2025-01-08',
      time: '12:15',
      distance: '5.1km',
      duration: '42분',
      trash: 47,
      calories: 320,
      route: '청계광장 → 고산자교 → 청계광장',
    },
  ];

  const weeklyStats = {
    totalDistance: '15.8km',
    totalTime: '2시간 7분',
    totalTrash: 129,
    totalCalories: 935,
    sessions: 4,
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>운동 기록</Text>
        <Text style={styles.headerSubtitle}>당신의 플로깅 여정</Text>
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Period Selector */}
        <View style={styles.periodSelector}>
          {periods.map((period) => (
            <TouchableOpacity
              key={period.key}
              style={[
                styles.periodButton,
                selectedPeriod === period.key && styles.periodButtonActive,
              ]}
              onPress={() => setSelectedPeriod(period.key)}
            >
              <Text
                style={[
                  styles.periodButtonText,
                  selectedPeriod === period.key && styles.periodButtonTextActive,
                ]}
              >
                {period.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Summary Stats */}
        <View style={styles.summaryContainer}>
          <View style={styles.summaryCard}>
            <View style={styles.summaryHeader}>
              <Text style={styles.summaryTitle}>이번 주 요약</Text>
              <Award size={20} color="#10B981" />
            </View>
            
            <View style={styles.summaryStats}>
              <View style={styles.summaryRow}>
                <View style={styles.summaryStat}>
                  <MapPin size={16} color="#6B7280" />
                  <Text style={styles.summaryValue}>{weeklyStats.totalDistance}</Text>
                  <Text style={styles.summaryLabel}>총 거리</Text>
                </View>
                <View style={styles.summaryStat}>
                  <Clock size={16} color="#6B7280" />
                  <Text style={styles.summaryValue}>{weeklyStats.totalTime}</Text>
                  <Text style={styles.summaryLabel}>총 시간</Text>
                </View>
              </View>
              
              <View style={styles.summaryRow}>
                <View style={styles.summaryStat}>
                  <Trash2 size={16} color="#6B7280" />
                  <Text style={styles.summaryValue}>{weeklyStats.totalTrash}</Text>
                  <Text style={styles.summaryLabel}>쓰레기 수집</Text>
                </View>
                <View style={styles.summaryStat}>
                  <Zap size={16} color="#6B7280" />
                  <Text style={styles.summaryValue}>{weeklyStats.totalCalories}</Text>
                  <Text style={styles.summaryLabel}>칼로리</Text>
                </View>
              </View>
            </View>
            
            <View style={styles.sessionsInfo}>
              <Text style={styles.sessionsText}>총 {weeklyStats.sessions}회 플로깅</Text>
              <TrendingUp size={16} color="#10B981" />
            </View>
          </View>
        </View>

        {/* Activity List */}
        <View style={styles.activitySection}>
          <Text style={styles.sectionTitle}>최근 활동</Text>
          
          {activities.map((activity) => (
            <TouchableOpacity key={activity.id} style={styles.activityCard}>
              <View style={styles.activityHeader}>
                <View style={styles.activityTitleContainer}>
                  <Text style={styles.activityTitle}>{activity.title}</Text>
                  <View style={styles.activityDateContainer}>
                    <Calendar size={14} color="#6B7280" />
                    <Text style={styles.activityDate}>
                      {activity.date} • {activity.time}
                    </Text>
                  </View>
                </View>
                <Text style={styles.activityDistance}>{activity.distance}</Text>
              </View>

              <View style={styles.activityRoute}>
                <MapPin size={14} color="#10B981" />
                <Text style={styles.routeText}>{activity.route}</Text>
              </View>

              <View style={styles.activityStats}>
                <View style={styles.activityStat}>
                  <Clock size={16} color="#6B7280" />
                  <Text style={styles.activityStatValue}>{activity.duration}</Text>
                </View>
                <View style={styles.activityStat}>
                  <Trash2 size={16} color="#6B7280" />
                  <Text style={styles.activityStatValue}>{activity.trash}개</Text>
                </View>
                <View style={styles.activityStat}>
                  <Zap size={16} color="#6B7280" />
                  <Text style={styles.activityStatValue}>{activity.calories}kcal</Text>
                </View>
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Achievement Section */}
        <View style={styles.achievementSection}>
          <Text style={styles.sectionTitle}>최근 성과</Text>
          <View style={styles.achievementCard}>
            <View style={styles.achievementContent}>
              <Award size={32} color="#10B981" />
              <View style={styles.achievementText}>
                <Text style={styles.achievementTitle}>환경 수호자</Text>
                <Text style={styles.achievementDescription}>
                  이번 달 100개 이상의 쓰레기를 수집했습니다!
                </Text>
              </View>
            </View>
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
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: '800',
    color: '#1F2937',
  },
  headerSubtitle: {
    fontSize: 16,
    color: '#6B7280',
    marginTop: 4,
    fontWeight: '500',
  },
  periodSelector: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    marginBottom: 20,
    gap: 8,
  },
  periodButton: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 8,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  periodButtonActive: {
    backgroundColor: '#10B981',
    borderColor: '#10B981',
  },
  periodButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B7280',
  },
  periodButtonTextActive: {
    color: '#ffffff',
  },
  summaryContainer: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  summaryCard: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  summaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  summaryTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1F2937',
  },
  summaryStats: {
    gap: 16,
  },
  summaryRow: {
    flexDirection: 'row',
    gap: 20,
  },
  summaryStat: {
    flex: 1,
    alignItems: 'center',
    gap: 8,
  },
  summaryValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1F2937',
  },
  summaryLabel: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  sessionsInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 20,
    gap: 8,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#F3F4F6',
  },
  sessionsText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#10B981',
  },
  activitySection: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1F2937',
    marginBottom: 16,
  },
  activityCard: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 12,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.03,
    shadowRadius: 4,
    elevation: 2,
  },
  activityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  activityTitleContainer: {
    flex: 1,
  },
  activityTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
  },
  activityDateContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
    gap: 6,
  },
  activityDate: {
    fontSize: 14,
    color: '#6B7280',
  },
  activityDistance: {
    fontSize: 18,
    fontWeight: '700',
    color: '#10B981',
  },
  activityRoute: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    gap: 6,
  },
  routeText: {
    fontSize: 14,
    color: '#6B7280',
    flex: 1,
  },
  activityStats: {
    flexDirection: 'row',
    gap: 24,
  },
  activityStat: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  activityStatValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1F2937',
  },
  achievementSection: {
    paddingHorizontal: 20,
    marginBottom: 24,
  },
  achievementCard: {
    backgroundColor: '#ffffff',
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 3,
  },
  achievementContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  achievementText: {
    flex: 1,
  },
  achievementTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#1F2937',
  },
  achievementDescription: {
    fontSize: 14,
    color: '#6B7280',
    marginTop: 4,
  },
});