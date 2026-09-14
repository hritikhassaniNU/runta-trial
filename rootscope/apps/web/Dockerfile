FROM node:22-alpine
WORKDIR /web
COPY apps/web/package.json ./
RUN npm install
COPY apps/web ./
ENV API_UPSTREAM=http://api:8000
EXPOSE 3000
CMD ["npm", "run", "dev"]
