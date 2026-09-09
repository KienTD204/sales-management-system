# GIT BRANCHING STRATEGY

## 1. Mục đích

Tài liệu này quy định chiến lược sử dụng nhánh Git cho dự án Website Quản lý Bán hàng cho Cửa hàng và Đại lý nhằm giúp các thành viên phát triển chức năng độc lập, hạn chế xung đột mã nguồn và đảm bảo nhánh chính luôn ổn định.

## 2. Các nhánh sử dụng

### main

Nhánh `main` chứa phiên bản ổn định của hệ thống.

Quy định:

* Không phát triển chức năng trực tiếp trên `main`.
* Không push code trực tiếp lên `main`.
* Chỉ merge từ `dev` sang `main` khi hệ thống hoặc milestone đã được kiểm tra và hoạt động ổn định.
* Phiên bản cuối cùng dùng để demo, release và nộp đồ án sẽ được lưu trên `main`.

### dev

Nhánh `dev` là nhánh tích hợp chính trong quá trình phát triển.

Quy định:

* Các chức năng sau khi hoàn thành sẽ được merge vào `dev`.
* `dev` dùng để tích hợp và kiểm thử các chức năng của Thành viên A và Thành viên B.
* Không nên phát triển chức năng lớn trực tiếp trên `dev`.
* Khi `dev` đã ổn định tại một milestone, có thể merge sang `main`.

### feature/*

Nhánh `feature/*` được sử dụng để phát triển từng chức năng riêng biệt.

Mỗi feature branch được tạo từ `dev`.

Ví dụ:

* `feature/auth`
* `feature/user-role`
* `feature/product`
* `feature/category`
* `feature/customer`
* `feature/pos`
* `feature/order`
* `feature/payment`
* `feature/invoice`
* `feature/employee`
* `feature/inventory`
* `feature/report`
* `feature/subscription`

Sau khi chức năng hoàn thành và được kiểm tra, feature branch sẽ được tạo Pull Request để merge trở lại `dev`.

## 3. Luồng làm việc

Luồng phát triển chung:

`dev → feature/* → dev → main`

Cụ thể:

1. Chuyển sang nhánh `dev`.
2. Cập nhật phiên bản mới nhất của `dev`.
3. Tạo feature branch mới từ `dev`.
4. Phát triển chức năng trên feature branch.
5. Commit các thay đổi.
6. Push feature branch lên GitHub.
7. Tạo Pull Request từ `feature/*` vào `dev`.
8. Thành viên còn lại review.
9. Merge feature branch vào `dev`.
10. Kiểm thử trên `dev`.
11. Khi milestone ổn định, merge `dev` vào `main`.

## 4. Quy tắc đặt tên branch

Feature mới:

`feature/<ten-chuc-nang>`

Ví dụ:

`feature/auth`

`feature/product`

`feature/order`

`feature/inventory`

Khi cần sửa lỗi có thể sử dụng:

`fix/<ten-loi>`

Ví dụ:

`fix/login-validation`

`fix/order-total`

## 5. Quy tắc commit

Commit message cần ngắn gọn và mô tả đúng thay đổi.

Các prefix sử dụng:

* `feat:` thêm chức năng mới.
* `fix:` sửa lỗi.
* `docs:` thay đổi tài liệu.
* `test:` thêm hoặc sửa kiểm thử.
* `refactor:` chỉnh sửa cấu trúc code nhưng không thay đổi chức năng.
* `chore:` các công việc cấu hình hoặc bảo trì khác.

Ví dụ:

`feat: implement user authentication`

`feat: add product CRUD`

`fix: prevent negative inventory`

`docs: update project scope`

`test: add authentication test cases`

## 6. Quy tắc chung

1. Không code trực tiếp trên `main`.
2. Không push trực tiếp lên `main`.
3. Mỗi chức năng mới nên có feature branch riêng.
4. Feature branch phải được tạo từ phiên bản `dev` mới nhất.
5. Feature hoàn thành phải merge về `dev`.
6. Nên sử dụng Pull Request trước khi merge.
7. Thành viên còn lại review Pull Request khi có thể.
8. Kiểm thử chức năng sau khi merge vào `dev`.
9. Chỉ merge `dev` sang `main` khi phiên bản đã ổn định.
10. Feature branch có thể xóa sau khi đã merge thành công.
