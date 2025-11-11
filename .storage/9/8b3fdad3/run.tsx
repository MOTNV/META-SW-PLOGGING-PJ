import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Dimensions } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Play, Pause, Square, MapPin, Clock, Trash2, Zap } from 'lucide-react-native';

const { width } = Dimensions.get('window');

export default function RunScreen() {
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState('00:00:00');
  const [distance, setDistance] = useState('0.00');
  const [trashCount, setTrashCount] = useState(0);
  const [calories, setCalories] = useState('0');

  const handleStart = () => {
    setIsRunning(true);
    setIsPaused(false);
  };

  const handlePause = () => {
    setIsPaused(!isPaused);
  };

  const handleStop = () => {
    setIsRunning(false);
    setIsPaused(false);
  };

  const handleTrashCollected = () => {
    setTrashCount(prev => prev + 1);
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>플로깅</Text>
        <Text style={styles.headerSubtitle}>
          {isRunning ? '진행 중' : '준비'}
        </Text>
      </View>

      {/* Main Stats */}
      <View style={styles.mainStats}>
        {/* Timer */}
        <View style={styles.timerContainer}>
          <Text style={styles.timerLabel}>시간</Text>
          <Text style={styles.timerValue}>{duration}</Text>
        </View>

        {/* Distance & Trash Counter */}
        <View style={styles.statsRow}>
          <View style={styles.statItem}>
            <MapPin size={20} color="#10B981" />
            <Text style={styles.statValue}>{distance}</Text>
            <Text style={styles.statLabel}>거리 (km)</Text>
          </View>
          <View style={styles.statItem}>
            <Trash2 size={20} color="#10B981" />
            <Text style={styles.statValue}>{trashCount}</Text>
            <Text style={styles.statLabel}>쓰레기 수집</Text>
          </View>
          <View style={styles.statItem}>
            <Zap size={20} color="#10B981" />
            <Text style={styles.statValue}>{calories}</Text>
            <Text style={styles.statLabel}>칼로리</Text>
          </View>
        </View>
      </View>

      {/* Map Placeholder */}
      <View style={styles.mapContainer}>
        <LinearGradient
          colors={['#E5E7EB', '#F3F4F6']}
          style={styles.mapPlaceholder}
        >
          <MapPin size={48} color="#9CA3AF" />
          <Text style={styles.mapText}>GPS 연결 중...</Text>
          <Text style={styles.mapSubtext}>운동을 시작하면 경로를 추적합니다</Text>
        </LinearGradient>
      </View>

      {/* Trash Collection Button */}
      <View style={styles.trashSection}>
        <TouchableOpacity 
          style={styles.trashButton}
          onPress={handleTrashCollected}
          disabled={!isRunning || isPaused}
        >
          <LinearGradient
            colors={['#34D399', '#10B981']}
            style={styles.trashButtonGradient}
          >
            <Trash2 size={24} color="#ffffff" />
            <Text style={styles.trashButtonText}>쓰레기 수집 +1</Text>
          </LinearGradient>
        </TouchableOpacity>
      </View>

      {/* Control Buttons */}
      <View style={styles.controls}>
        {!isRunning ? (
          <TouchableOpacity style={styles.startButton} onPress={handleStart}>
            <LinearGradient
              colors={['#10B981', '#059669']}
              style={styles.startButtonGradient}
            >
              <Play size={32} color="#ffffff" />
            </LinearGradient>
          </TouchableOpacity>
        ) : (
          <View style={styles.runningControls}>
            <TouchableOpacity 
              style={styles.controlButton}
              onPress={handlePause}
            >
              <View style={styles.controlButtonBackground}>
                {isPaused ? (
                  <Play size={24} color="#10B981" />
                ) : (
                  <Pause size={24} color="#10B981" />
                )}
              </View>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={styles.stopButton}
              onPress={handleStop}
            >
              <View style={styles.stopButtonBackground}>
                <Square size={24} color="#ffffff" />
              </View>
            </TouchableOpacity>
          </View>
        )}
      </View>

      {/* Quick Stats */}
      <View style={styles.quickStats}>
        <View style={styles.quickStatItem}>
          <Text style={styles.quickStatValue}>5.2</Text>
          <Text style={styles.quickStatLabel}>평균 속도</Text>
          <Text style={styles.quickStatUnit}>km/h</Text>
        </View>
        <View style={styles.quickStatItem}>
          <Text style={styles.quickStatValue}>7'30"</Text>
          <Text style={styles.quickStatLabel}>평균 페이스</Text>
          <Text style={styles.quickStatUnit}>분/km</Text>
        </View>
        <View style={styles.quickStatItem}>
          <Text style={styles.quickStatValue}>125</Text>
          <Text style={styles.quickStatLabel}>평균 심박</Text>
          <Text style={styles.quickStatUnit}>bpm</Text>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },
  header: {
    padding: 20,
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: '800',
    color: '#1F2937',
  },
  headerSubtitle: {
    fontSize: 16,
    color: '#6B7280',
    marginTop: 4,
    fontWeight: '500',
  },
  mainStats: {
    padding: 20,
    alignItems: 'center',
  },
  timerContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  timerLabel: {
    fontSize: 14,
    color: '#6B7280',
    fontWeight: '500',
  },
  timerValue: {
    fontSize: 48,
    fontWeight: '800',
    color: '#1F2937',
    marginTop: 8,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 32,
  },
  statItem: {
    alignItems: 'center',
    gap: 8,
  },
  statValue: {
    fontSize: 24,
    fontWeight: '700',
    color: '#1F2937',
  },
  statLabel: {
    fontSize: 12,
    color: '#6B7280',
    fontWeight: '500',
  },
  mapContainer: {
    flex: 1,
    margin: 20,
    borderRadius: 12,
    overflow: 'hidden',
  },
  mapPlaceholder: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  mapText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#6B7280',
  },
  mapSubtext: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
  },
  trashSection: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  trashButton: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  trashButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 16,
    gap: 12,
  },
  trashButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
  },
  controls: {
    paddingHorizontal: 20,
    alignItems: 'center',
    marginBottom: 20,
  },
  startButton: {
    borderRadius: 40,
    overflow: 'hidden',
  },
  startButtonGradient: {
    width: 80,
    height: 80,
    alignItems: 'center',
    justifyContent: 'center',
  },
  runningControls: {
    flexDirection: 'row',
    gap: 24,
  },
  controlButton: {
    borderRadius: 30,
  },
  controlButtonBackground: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#ffffff',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  stopButton: {
    borderRadius: 30,
  },
  stopButtonBackground: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: '#EF4444',
    alignItems: 'center',
    justifyContent: 'center',
  },
  quickStats: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingBottom: 20,
    gap: 16,
  },
  quickStatItem: {
    flex: 1,
    backgroundColor: '#F9FAFB',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
  },
  quickStatValue: {
    fontSize: 18,
    fontWeight: '700',
    color: '#1F2937',
  },
  quickStatLabel: {
    fontSize: 12,
    color: '#6B7280',
    marginTop: 4,
    textAlign: 'center',
  },
  quickStatUnit: {
    fontSize: 10,
    color: '#9CA3AF',
    marginTop: 2,
  },
});