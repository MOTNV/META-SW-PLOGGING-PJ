import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Alert, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as Location from 'expo-location';
import MapContainer from '../../components/MapContainer';

interface LocationData {
  latitude: number;
  longitude: number;
  accuracy?: number;
  speed?: number;
  timestamp: string;
}

export default function RunScreen() {
  const [isRunning, setIsRunning] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [distance, setDistance] = useState(0);
  const [currentLocation, setCurrentLocation] = useState<LocationData | null>(null);
  const [route, setRoute] = useState<LocationData[]>([]);
  const [trashCount, setTrashCount] = useState(0);
  const [calories, setCalories] = useState(0);
  const [locationPermission, setLocationPermission] = useState<boolean>(false);
  const [locationError, setLocationError] = useState<string>('');

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const locationWatchRef = useRef<Location.LocationSubscription | null>(null);

  // 위치 권한 요청
  useEffect(() => {
    requestLocationPermission();
    return () => {
      if (locationWatchRef.current) {
        locationWatchRef.current.remove();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const requestLocationPermission = async () => {
    try {
      setLocationError('');
      
      // 위치 서비스 활성화 확인
      const serviceEnabled = await Location.hasServicesEnabledAsync();
      if (!serviceEnabled) {
        setLocationError('위치 서비스가 비활성화되어 있습니다. 설정에서 위치 서비스를 활성화해주세요.');
        return;
      }

      // 권한 상태 확인
      let { status } = await Location.getForegroundPermissionsAsync();
      
      if (status !== 'granted') {
        // 권한 요청
        const { status: newStatus } = await Location.requestForegroundPermissionsAsync();
        status = newStatus;
      }

      if (status === 'granted') {
        setLocationPermission(true);
        setLocationError('');
        
        // 초기 위치 가져오기
        try {
          const location = await Location.getCurrentPositionAsync({
            accuracy: Location.Accuracy.High,
            timeInterval: 1000,
            distanceInterval: 1,
          });
          
          const locationData: LocationData = {
            latitude: location.coords.latitude,
            longitude: location.coords.longitude,
            accuracy: location.coords.accuracy || undefined,
            speed: location.coords.speed || undefined,
            timestamp: new Date().toISOString(),
          };
          
          setCurrentLocation(locationData);
        } catch (error) {
          console.error('초기 위치 가져오기 실패:', error);
          setLocationError('현재 위치를 가져올 수 없습니다. GPS 신호를 확인해주세요.');
        }
      } else {
        setLocationPermission(false);
        setLocationError('위치 권한이 필요합니다. 설정에서 위치 권한을 허용해주세요.');
      }
    } catch (error) {
      console.error('위치 권한 요청 실패:', error);
      setLocationError('위치 권한 요청 중 오류가 발생했습니다.');
    }
  };

  // 실시간 위치 추적 시작
  const startLocationTracking = async () => {
    if (!locationPermission) {
      await requestLocationPermission();
      return;
    }

    try {
      locationWatchRef.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 2000, // 2초마다 업데이트
          distanceInterval: 5, // 5미터 이동시 업데이트
        },
        (location) => {
          const locationData: LocationData = {
            latitude: location.coords.latitude,
            longitude: location.coords.longitude,
            accuracy: location.coords.accuracy || undefined,
            speed: location.coords.speed || undefined,
            timestamp: new Date().toISOString(),
          };

          setCurrentLocation(locationData);
          
          // 운동 중일 때만 경로에 추가
          if (isRunning && !isPaused) {
            setRoute(prevRoute => {
              const newRoute = [...prevRoute, locationData];
              
              // 거리 계산 (이전 위치와 현재 위치 사이의 거리)
              if (prevRoute.length > 0) {
                const lastLocation = prevRoute[prevRoute.length - 1];
                const distanceIncrement = calculateDistance(
                  lastLocation.latitude,
                  lastLocation.longitude,
                  locationData.latitude,
                  locationData.longitude
                );
                setDistance(prevDistance => prevDistance + distanceIncrement);
              }
              
              return newRoute;
            });
          }
        }
      );
    } catch (error) {
      console.error('위치 추적 시작 실패:', error);
      setLocationError('위치 추적을 시작할 수 없습니다.');
    }
  };

  // 위치 추적 중지
  const stopLocationTracking = () => {
    if (locationWatchRef.current) {
      locationWatchRef.current.remove();
      locationWatchRef.current = null;
    }
  };

  // 두 지점 간의 거리 계산 (Haversine formula)
  const calculateDistance = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const R = 6371; // 지구 반지름 (km)
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = 
      Math.sin(dLat/2) * Math.sin(dLat/2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
      Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
  };

  // 칼로리 계산 (대략적인 계산)
  const calculateCalories = (distanceKm: number, durationMinutes: number): number => {
    // 평균 체중 70kg, 달리기 시 분당 10칼로리 소모 가정
    const caloriesPerMinute = 10;
    return Math.round(durationMinutes * caloriesPerMinute);
  };

  // 타이머 시작
  const startTimer = () => {
    timerRef.current = setInterval(() => {
      setDuration(prev => {
        const newDuration = prev + 1;
        setCalories(calculateCalories(distance, newDuration / 60));
        return newDuration;
      });
    }, 1000);
  };

  // 타이머 중지
  const stopTimer = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  // 운동 시작
  const handleStart = async () => {
    if (!locationPermission) {
      Alert.alert('위치 권한 필요', '플로깅을 시작하려면 위치 권한이 필요합니다.');
      await requestLocationPermission();
      return;
    }

    setIsRunning(true);
    setIsPaused(false);
    startTimer();
    await startLocationTracking();
  };

  // 운동 일시정지
  const handlePause = () => {
    setIsPaused(!isPaused);
    if (!isPaused) {
      stopTimer();
    } else {
      startTimer();
    }
  };

  // 운동 종료
  const handleStop = () => {
    Alert.alert(
      '운동 종료',
      '정말로 운동을 종료하시겠습니까?',
      [
        { text: '취소', style: 'cancel' },
        {
          text: '종료',
          style: 'destructive',
          onPress: () => {
            setIsRunning(false);
            setIsPaused(false);
            stopTimer();
            stopLocationTracking();
            
            // 운동 결과 저장 로직 추가 가능
            Alert.alert(
              '운동 완료!',
              `거리: ${distance.toFixed(2)}km\n시간: ${Math.floor(duration / 60)}분 ${duration % 60}초\n칼로리: ${calories}kcal\n쓰레기: ${trashCount}개`,
              [
                {
                  text: '확인',
                  onPress: () => {
                    // 초기화
                    setDuration(0);
                    setDistance(0);
                    setRoute([]);
                    setTrashCount(0);
                    setCalories(0);
                  }
                }
              ]
            );
          }
        }
      ]
    );
  };

  // 쓰레기 수집
  const handleTrashCollection = () => {
    setTrashCount(prev => prev + 1);
    Alert.alert('쓰레기 수집!', `총 ${trashCount + 1}개의 쓰레기를 수집했습니다.`);
  };

  // 시간 포맷팅
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <View style={styles.container}>
      {/* 맵 영역 */}
      <View style={styles.mapContainer}>
        <MapContainer
          location={currentLocation}
          route={route}
          style={styles.map}
          onMapReady={() => console.log('맵이 준비되었습니다')}
        />
        
        {locationError ? (
          <View style={styles.errorContainer}>
            <Text style={styles.errorText}>{locationError}</Text>
            <TouchableOpacity 
              style={styles.retryButton} 
              onPress={requestLocationPermission}
            >
              <Text style={styles.retryButtonText}>다시 시도</Text>
            </TouchableOpacity>
          </View>
        ) : null}
      </View>

      {/* 통계 정보 */}
      <View style={styles.statsContainer}>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{formatTime(duration)}</Text>
          <Text style={styles.statLabel}>시간</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{distance.toFixed(2)}</Text>
          <Text style={styles.statLabel}>거리 (km)</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{calories}</Text>
          <Text style={styles.statLabel}>칼로리</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{trashCount}</Text>
          <Text style={styles.statLabel}>쓰레기</Text>
        </View>
      </View>

      {/* 컨트롤 버튼 */}
      <View style={styles.controlsContainer}>
        {!isRunning ? (
          <TouchableOpacity 
            style={[styles.controlButton, styles.startButton]} 
            onPress={handleStart}
            disabled={!locationPermission}
          >
            <Ionicons name="play" size={32} color="white" />
            <Text style={styles.controlButtonText}>시작</Text>
          </TouchableOpacity>
        ) : (
          <View style={styles.runningControls}>
            <TouchableOpacity 
              style={[styles.controlButton, isPaused ? styles.resumeButton : styles.pauseButton]} 
              onPress={handlePause}
            >
              <Ionicons name={isPaused ? "play" : "pause"} size={24} color="white" />
              <Text style={styles.controlButtonText}>{isPaused ? "재개" : "일시정지"}</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.controlButton, styles.trashButton]} 
              onPress={handleTrashCollection}
            >
              <Ionicons name="trash" size={24} color="white" />
              <Text style={styles.controlButtonText}>쓰레기 수집</Text>
            </TouchableOpacity>
            
            <TouchableOpacity 
              style={[styles.controlButton, styles.stopButton]} 
              onPress={handleStop}
            >
              <Ionicons name="stop" size={24} color="white" />
              <Text style={styles.controlButtonText}>종료</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  mapContainer: {
    flex: 1,
    position: 'relative',
  },
  map: {
    flex: 1,
  },
  errorContainer: {
    position: 'absolute',
    top: 20,
    left: 20,
    right: 20,
    backgroundColor: 'rgba(255, 0, 0, 0.9)',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  errorText: {
    color: 'white',
    fontSize: 14,
    textAlign: 'center',
    marginBottom: 10,
  },
  retryButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 5,
  },
  retryButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: 'bold',
  },
  statsContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    paddingVertical: 20,
    paddingHorizontal: 10,
    justifyContent: 'space-around',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  controlsContainer: {
    backgroundColor: 'white',
    paddingVertical: 20,
    paddingHorizontal: 20,
    paddingBottom: 40,
  },
  controlButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 15,
    paddingHorizontal: 20,
    borderRadius: 25,
    marginHorizontal: 5,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
  },
  controlButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
    marginLeft: 8,
  },
  startButton: {
    backgroundColor: '#4CAF50',
    flex: 1,
  },
  runningControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  pauseButton: {
    backgroundColor: '#FF9800',
    flex: 1,
  },
  resumeButton: {
    backgroundColor: '#4CAF50',
    flex: 1,
  },
  trashButton: {
    backgroundColor: '#2196F3',
    flex: 1,
  },
  stopButton: {
    backgroundColor: '#f44336',
    flex: 1,
  },
});