import React from 'react';
import { View, Text, StyleSheet, ScrollView, Platform } from 'react-native';

export default function MapIntegrationGuide() {
  if (Platform.OS !== 'web') {
    return (
      <ScrollView style={styles.container}>
        <View style={styles.section}>
          <Text style={styles.title}>📱 네이티브 앱 맵 연동 가이드</Text>
          
          <View style={styles.guideSection}>
            <Text style={styles.sectionTitle}>1. React Native Maps 사용</Text>
            <Text style={styles.code}>npm install react-native-maps</Text>
            <Text style={styles.description}>
              가장 인기 있는 React Native 맵 라이브러리입니다.
            </Text>
          </View>

          <View style={styles.guideSection}>
            <Text style={styles.sectionTitle}>2. 카카오맵 SDK</Text>
            <Text style={styles.description}>
              카카오 네이티브 맵 SDK를 React Native와 연동하여 사용할 수 있습니다.
            </Text>
          </View>
        </View>
      </ScrollView>
    );
  }

  return (
    <div style={webStyles.container}>
      <div style={webStyles.header}>
        <h1 style={webStyles.title}>🗺️ 웹 맵 API 연동 가이드</h1>
        <p style={webStyles.subtitle}>카카오맵 또는 네이버 맵 API를 쉽게 연동하세요</p>
      </div>

      <div style={webStyles.content}>
        {/* 카카오맵 가이드 */}
        <div style={webStyles.section}>
          <h2 style={webStyles.sectionTitle}>🟡 카카오맵 API 연동</h2>
          
          <div style={webStyles.step}>
            <h3 style={webStyles.stepTitle}>1. API 키 발급</h3>
            <p style={webStyles.stepDescription}>
              <a href="https://developers.kakao.com/" target="_blank" rel="noopener noreferrer" style={webStyles.link}>
                카카오 개발자 센터
              </a>에서 애플리케이션 등록 후 JavaScript 키를 발급받으세요.
            </p>
          </div>

          <div style={webStyles.step}>
            <h3 style={webStyles.stepTitle}>2. 스크립트 추가</h3>
            <div style={webStyles.codeBlock}>
              <code>{`<script type="text/javascript" src="//dapi.kakao.com/v2/maps/sdk.js?appkey=YOUR_APP_KEY"></script>`}</code>
            </div>
          </div>

          <div style={webStyles.step}>
            <h3 style={webStyles.stepTitle}>3. 맵 초기화 코드 예시</h3>
            <div style={webStyles.codeBlock}>
              <pre style={webStyles.code}>{`// MapContainer.tsx 내부에서 사용
useEffect(() => {
  if (window.kakao && window.kakao.maps) {
    const container = mapContainerRef.current;
    const options = {
      center: new window.kakao.maps.LatLng(37.5665, 126.9780),
      level: 3
    };
    const map = new window.kakao.maps.Map(container, options);
    
    // 현재 위치 마커 추가
    if (location) {
      const markerPosition = new window.kakao.maps.LatLng(
        location.latitude, 
        location.longitude
      );
      const marker = new window.kakao.maps.Marker({
        position: markerPosition
      });
      marker.setMap(map);
    }
  }
}, [location]);`}</pre>
            </div>
          </div>
        </div>

        {/* 네이버 맵 가이드 */}
        <div style={webStyles.section}>
          <h2 style={webStyles.sectionTitle}>🟢 네이버 맵 API 연동</h2>
          
          <div style={webStyles.step}>
            <h3 style={webStyles.stepTitle}>1. API 키 발급</h3>
            <p style={webStyles.stepDescription}>
              <a href="https://www.ncloud.com/product/applicationService/maps" target="_blank" rel="noopener noreferrer" style={webStyles.link}>
                네이버 클라우드 플랫폼
              </a>에서 Maps API 서비스 신청 후 클라이언트 ID를 발급받으세요.
            </p>
          </div>

          <div style={webStyles.step}>
            <h3 style={webStyles.stepTitle}>2. 스크립트 추가</h3>
            <div style={webStyles.codeBlock}>
              <code>{`<script type="text/javascript" src="https://openapi.map.naver.com/openapi/v3/maps.js?ncpClientId=YOUR_CLIENT_ID"></script>`}</code>
            </div>
          </div>

          <div style={webStyles.step}>
            <h3 style={webStyles.stepTitle}>3. 맵 초기화 코드 예시</h3>
            <div style={webStyles.codeBlock}>
              <pre style={webStyles.code}>{`// MapContainer.tsx 내부에서 사용
useEffect(() => {
  if (window.naver && window.naver.maps) {
    const mapOptions = {
      center: new window.naver.maps.LatLng(37.5665, 126.9780),
      zoom: 15
    };
    const map = new window.naver.maps.Map(mapContainerRef.current, mapOptions);
    
    // 현재 위치 마커 추가
    if (location) {
      const marker = new window.naver.maps.Marker({
        position: new window.naver.maps.LatLng(
          location.latitude, 
          location.longitude
        ),
        map: map
      });
    }
  }
}, [location]);`}</pre>
            </div>
          </div>
        </div>

        {/* 구현 팁 */}
        <div style={webStyles.section}>
          <h2 style={webStyles.sectionTitle}>💡 구현 팁</h2>
          
          <div style={webStyles.tipCard}>
            <h4 style={webStyles.tipTitle}>🔄 실시간 위치 업데이트</h4>
            <p style={webStyles.tipDescription}>
              GPS 위치가 변경될 때마다 맵의 중심을 이동하고 마커 위치를 업데이트하세요.
            </p>
          </div>

          <div style={webStyles.tipCard}>
            <h4 style={webStyles.tipTitle}>🛤️ 경로 그리기</h4>
            <p style={webStyles.tipDescription}>
              route 배열의 좌표들을 연결하여 Polyline으로 경로를 그릴 수 있습니다.
            </p>
          </div>

          <div style={webStyles.tipCard}>
            <h4 style={webStyles.tipTitle}>📱 반응형 디자인</h4>
            <p style={webStyles.tipDescription}>
              모바일과 데스크톱에서 모두 잘 보이도록 맵 크기를 조정하세요.
            </p>
          </div>
        </div>

        {/* 파일 구조 */}
        <div style={webStyles.section}>
          <h2 style={webStyles.sectionTitle}>📁 권장 파일 구조</h2>
          <div style={webStyles.codeBlock}>
            <pre style={webStyles.code}>{`components/
├── MapContainer.tsx          // 현재 파일 (맵 API 연동)
├── KakaoMapView.tsx         // 카카오맵 전용 컴포넌트
├── NaverMapView.tsx         // 네이버맵 전용 컴포넌트
└── MapIntegrationGuide.tsx  // 이 가이드 파일

// 사용 예시
import MapContainer from './components/MapContainer';
// 또는
import KakaoMapView from './components/KakaoMapView';`}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 20,
  },
  section: {
    marginBottom: 30,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 20,
    textAlign: 'center',
  },
  guideSection: {
    marginBottom: 20,
    padding: 15,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  code: {
    fontFamily: 'monospace',
    backgroundColor: '#e9ecef',
    padding: 8,
    borderRadius: 4,
    fontSize: 12,
    color: '#495057',
  },
  description: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    marginTop: 8,
  },
});

const webStyles = {
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '20px',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  header: {
    textAlign: 'center' as const,
    marginBottom: '40px',
    padding: '30px',
    background: 'linear-gradient(135deg, #4CAF50, #45a049)',
    color: 'white',
    borderRadius: '12px',
  },
  title: {
    fontSize: '2.5rem',
    margin: '0 0 10px 0',
    fontWeight: 'bold',
  },
  subtitle: {
    fontSize: '1.2rem',
    margin: 0,
    opacity: 0.9,
  },
  content: {
    display: 'grid',
    gap: '30px',
  },
  section: {
    background: 'white',
    padding: '30px',
    borderRadius: '12px',
    boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
  },
  sectionTitle: {
    fontSize: '1.8rem',
    color: '#333',
    marginBottom: '20px',
    borderBottom: '3px solid #4CAF50',
    paddingBottom: '10px',
  },
  step: {
    marginBottom: '25px',
    padding: '20px',
    background: '#f8f9fa',
    borderRadius: '8px',
    borderLeft: '4px solid #4CAF50',
  },
  stepTitle: {
    fontSize: '1.3rem',
    color: '#333',
    marginBottom: '10px',
    fontWeight: 'bold',
  },
  stepDescription: {
    fontSize: '1rem',
    color: '#666',
    lineHeight: '1.6',
    margin: 0,
  },
  link: {
    color: '#4CAF50',
    textDecoration: 'none',
    fontWeight: 'bold',
  },
  codeBlock: {
    background: '#2d3748',
    color: '#e2e8f0',
    padding: '15px',
    borderRadius: '6px',
    marginTop: '10px',
    overflow: 'auto',
  },
  code: {
    fontFamily: 'Monaco, Consolas, monospace',
    fontSize: '0.9rem',
    lineHeight: '1.5',
    margin: 0,
    whiteSpace: 'pre-wrap' as const,
  },
  tipCard: {
    background: '#e8f5e8',
    padding: '20px',
    borderRadius: '8px',
    marginBottom: '15px',
    border: '1px solid #c8e6c9',
  },
  tipTitle: {
    fontSize: '1.1rem',
    color: '#2e7d32',
    marginBottom: '8px',
    fontWeight: 'bold',
  },
  tipDescription: {
    fontSize: '1rem',
    color: '#4a5568',
    lineHeight: '1.5',
    margin: 0,
  },
};