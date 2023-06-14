import './App.css';
import React from 'react';
import { useNavigate } from 'react-router-dom';

import { Upload, message, Space } from 'antd';
import { Layout, Menu } from 'antd';
import { Card } from 'antd';
import { CloudUploadOutlined } from '@ant-design/icons';

import axios from 'axios';

/**
 * To avoid the CORS issue, API address must be separated between dev mode and production mode.
 * Dev mode: /api/{API}
 * production mode: /{API}
 */
const PROXY = window.location.hostname === 'localhost' ? '/api' : '';
const INPUTURL = `${PROXY}/Input`;

const { Header, Content, Footer } = Layout;

/**
 * Check the file is .ste file. 
 * @param {string} name 
 * @returns {boolean}
 */
function CheckExtention(name) {
  let words = name.split('.');
  let ext = words[words.length - 1];
    if (ext === 'ste') {
      return true;
  }
}

function MainPage() {
  const navigate = useNavigate();

  //Logo
  /**
   * Refresh the page if the user click the logo.
   * @param {*} event 
   */
  const onClickLogo = (event) => {
    navigate(0);
  };

  // Upload TAC report
  /**
   * Upload the formData(.ste file) to server.
   * Call /Input API to the server with body parameter
   * - Parameter
   *  formData: Input STE file
   * @param {FormData} formData 
   */
  const upload = async(formData) => {
    const hideMessage = message.loading(`Uploading TAC report to server`, 0);
    try{
      const res = await axios.post(INPUTURL, formData);
      const inputInfo = JSON.parse(res.data);
      navigate(`/Search`, { 
        state: {
          inputInfoParams: inputInfo,
        }});
      message.success(`Success to parse ste file`);
    }
    catch{
      message.error(`Fail to upload the TAC report`);
    }
    finally {
      hideMessage();
    }
  };

  /**
   * Notify when the user drops the ste file into CI Finder.
   * @param {*} event 
   */
  const onDrop = (event) => {
    message.success(`TAC report added`);
  };

  
  /**
   * Notify when the user selects the ste file and try to upload.
   * @param {*} event 
   */
  const onChangeUpload = async (event) => {
    const file = event.file;
    const reader = new FileReader();
    const formData = new FormData();
    if (CheckExtention(file.name) === true) { // If input is .ste
      reader.onload = (event) => {
        formData.append("file", file);
        formData.append("fileName", file.name);
        upload(formData);
      };
      reader.readAsArrayBuffer(file);
    } 
    else {
      message.error(`This file is not a ste file.`);
    }
  };

  return (
    <>
      <Layout className="layout">
        <Header
          style={{ backgroundColor: "#2185D0" }}
        >
          <div className="logo" onClick={onClickLogo} />
          <Menu
            style={{ backgroundColor: "#2185D0", color: "#D0D0D0" }}
            mode="horizontal"
            defaultSelectedKeys={['1']}
          />
        </Header>
        <Layout style={{ minHeight: '80vh' }}>
          <Content style={{
            padding: '3% 0',
            width: '100%',
            display: 'flex',
            justifyContent: 'center',
          }}
          >
            <Space direction="vertical"
              size="middle"
              style={{
                display: 'flex',
                width: '800px',
              }}
            >
              <Card
                style={{
                  width: '100%',
                  height: 600,
                  maxHeight: 600,
                  padding: '1% 2%',
                  overflow: "auto"
                }}
              >
                <Space
                  direction="vertical"
                  size="small"
                  style={{
                    display: 'flex',
                  }}
                >
                  <p className="logoMain" align="center">
                    Landslide CI Finder
                  </p>
                  <p align="center">Analyze the customer's one-side-nodal test suite (.ste) <br />
                    Recommend most similar B2B test suites automatically.</p>
                  <Upload.Dragger
                    onDrop={onDrop}
                    onChange={onChangeUpload}
                    showUploadList={false}
                    beforeUpload={() => false}
                  >
                    <p className="ant-upload-drag-icon">
                      <CloudUploadOutlined />
                    </p>
                    <p className="ant-upload-text">
                      Upload the Customer's test suite
                    </p>
                    <p className="ant-upload-hint">
                      Only .ste file is allowed.
                    </p>
                  </Upload.Dragger>
                  <p align="center" >
                    <b> - Caution - </b> <br /> <br />
                    1. The ste file must include at least 1 test case. <br />
                    2. Only 1 ste could be analyzed. (No multiple ste files)
                  </p>
                </Space>
              </Card>
            </Space>
          </Content>
        </Layout>
        <Footer style={{ textAlign: 'center' }}>©2023 Spirent Communications, Inc. All rights reserved.</Footer>
      </Layout>
    </>
  );
}

export default MainPage;