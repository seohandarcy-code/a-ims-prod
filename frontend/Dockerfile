# PDEP 배포용 프론트엔드 이미지 (multi-stage: Vite 빌드 -> nginx 정적 서빙)
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Vite 환경변수는 빌드 시점에 번들에 고정되므로, 배포 환경별 백엔드 주소를
# --build-arg로 주입해 .env.production을 생성한 뒤 빌드한다.
ARG VITE_API_BASE_URL
RUN echo "VITE_API_BASE_URL=${VITE_API_BASE_URL}" > .env.production
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
