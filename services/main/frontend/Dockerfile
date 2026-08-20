FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .
RUN npm test
RUN npm run build -- --configuration production

EXPOSE 4200

CMD ["node", "serve-static.mjs"]
