import './App.css';
import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

import { Upload, message, Button, Space, Popover } from 'antd';
import { Layout, Menu } from 'antd';
import { Card, Checkbox, Col, Row } from 'antd';
import { Divider } from 'antd';
import { CloudUploadOutlined } from '@ant-design/icons';
import { Descriptions } from 'antd';
import { Form, InputNumber } from 'antd';
import { Collapse } from 'antd';

import axios from 'axios';

/**
 * To avoid the CORS issue, API address must be separated between dev mode and production mode.
 * Dev mode: /api/{API}
 * production mode: /{API}
 */
const PROXY = window.location.hostname === 'localhost' ? '/api' : '';
const INPUTURL = `${PROXY}/Input`;
const RESULTURL = `${PROXY}/Result`;

const { Header, Content, Footer } = Layout;
const { Panel } = Collapse;

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

/**
 * Convert key-value object to pydantic model.
 * @param {Object} nestedObj 
 * @returns {Array} 
 */
function ChangeObj2Pydantic(nestedObj) {
  let pydanticModel = [];
  for (let key of Object.keys(nestedObj)) {
    pydanticModel.push({
      testCase: key,
      items: nestedObj[key],
    })
  }
  return pydanticModel
}

/**
 * Check the string variable is valid. Try to filter out meaningless string variable. 
 * @param {string} TCL Name of string TCL Variable
 * @param {string} stringVal Value of string TCL Variable
 * @returns {boolean} 
 */
function IsValidStringVariable(TCL, stringVal) {
  const bytesPattern = /^0x[a-fA-F0-9_]+/;
  const bytePattern = /^[a-fA-F0-9_]{4}/;
  const addressPattern = /[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/;
  const ipv4Pattern = /((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])/;
  const ipv6Pattern = /(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))/;
  const portPattern = /[a-zA-Z]*#\(N[a-zA-Z0-9 /]+\)/;
  const numberPattern = /[a-zA-Z]*#\([a-zA-Z0-9 /]+\)/;

  if ((bytesPattern.test(stringVal) === true) ||
    (bytePattern.test(stringVal) === true) ||
    (addressPattern.test(stringVal) === true) ||
    (ipv4Pattern.test(stringVal) === true) ||
    (ipv6Pattern.test(stringVal) === true) ||
    (portPattern.test(stringVal) === true) ||
    (numberPattern.test(stringVal) === true) ||
    (TCL === "TestType") || 
    (TCL === "CommandSequence") || 
    (TCL === "TestActivity") ||
    (TCL.includes("_") === true)
  ) {
    return false;
  } 
  return true;
}



function MainPage() {
  const [inputInfo, setInputInfo] = useState(null);
  // const inputInfo = useRef(null);
  const [topk, setTopk] = useState({
    value: 30,
  });
  const [checkedBoolTclObj, setcheckedBoolTclObj] = useState({});
  const [checkedStringTclObj, setcheckedStringTclObj] = useState({});
  const finalRequest = {
    testCaseBoolean: [], // checkedBoolTclObj will be stored
    testCaseString: [], // checkedBoolTclObj will be stored
    topk: -1,
  };
  const navigate = useNavigate();


  //Logo
  /**
   * Refresh the page if the user click the logo.
   * @param {*} event 
   */
  const onClickLogo = (event) => {
    navigate(0);
  };

  // Information
  /**
   * Show Input STE's information via JSX
   * @returns 
   */
  const showInfo = () => {
    let input = {};
    let tcNameList = {};
    let isB2B = Boolean();
    
    input = inputInfo;

    tcNameList = Object.keys(input.tclData).map((tcName) => tcName+' ('+input.tclData[tcName].string.TestActivity+')');
    tcNameList.sort();

    return (
      <>
        <Descriptions.Item label="Name" span={2}>
          {input.name}
        </Descriptions.Item>
        <Descriptions.Item label="Number of test case">
          {tcNameList.length}
        </Descriptions.Item>
        <Descriptions.Item label="Name of test case" span={2}>
          {tcNameList.map((name, _) => (
            <Col key={name}>
              {name}
            </Col>
          ))}
        </Descriptions.Item>
        {isB2B && (
          <Descriptions.Item label="Score">
            {input.score}
          </Descriptions.Item>
        )}
      </>
    );
  };


  // CheckBox Slot
  /**
   * Make the object about "Test case - checked variable list" and set it to the state.
   * @param {string} TC Name of test case 
   * @param {Array} checkedValues List of current checked variables
   */
  const onChangeBoolCheckBox = (TC, checkedValues) => {
    if (checkedValues.length === 0) {
      let tmpcheckedBoolTclObj = checkedBoolTclObj;
      delete tmpcheckedBoolTclObj[TC];
      setcheckedBoolTclObj(tmpcheckedBoolTclObj);
    } else {
      setcheckedBoolTclObj({...checkedBoolTclObj, [TC]: checkedValues});
    }
  };

  /**
   * Make the object about "Test case - checked variable list" and set it to the state.
   * @param {string} TC Name of test case 
   * @param {Array} checkedValues List of current checked variables
   */
  const onChangeStringCheckBox = (TC, checkedValues) => {
    if (checkedValues.length === 0) {
      let tmpcheckedStringTclObj = checkedStringTclObj;
      delete tmpcheckedStringTclObj[TC];
      setcheckedStringTclObj(tmpcheckedStringTclObj);
    } else {
      setcheckedStringTclObj({...checkedStringTclObj, [TC]: checkedValues});
    }
  };

  /**
   * Show whole check list of searching CI test. 
   * @returns 
   */
  const showCheckList = () => {
    let enabledBoolTclObj = {};
    let validStringTclObj = {};
    let input = inputInfo;
    let inputTC = Object.keys(input.tclData);
    
    for (let TC of inputTC) {
      // Boolean Checkboxes
      enabledBoolTclObj[TC] = [];
      for (let TCL of Object.keys(input.tclData[TC].boolean)) {
        if (input.tclData[TC].boolean[TCL] === true) {
          enabledBoolTclObj[TC].push(TCL);
        }
      }

      // String Checkboxes
      validStringTclObj[TC] = [];
      for (let TCL of Object.keys(input.tclData[TC].string)) {
        if (IsValidStringVariable(TCL, input.tclData[TC].string[TCL]) === true) {
          validStringTclObj[TC].push(TCL);
        }
      }
    }

    return (
      <div
        style={{padding: '1% 2%'}}
      >
        {inputTC.map((TC, _) => (
          <>
            <Divider
              orientation="left"
              key={TC}
            >
              {TC}
            </Divider>
            <Divider
              orientation="center"
              key="Boolean"
            >
              Boolean
            </Divider>
            <Checkbox.Group style={{ width: '100%' }} onChange={(e) => onChangeBoolCheckBox(TC, e)}>
              <Row gutter={16}>
                {enabledBoolTclObj[TC].map((TCL, _) => (
                  <Col span={8} key={TCL}>
                    <Checkbox value={TCL}>{TCL}</Checkbox>
                  </Col>
                ))}
              </Row>
            </Checkbox.Group>
            <Divider
              orientation="center"
              key="String"
            >
              String
            </Divider>
            <Checkbox.Group style={{ width: '100%' }} onChange={(e) => onChangeStringCheckBox(TC, e)}>
              <Row gutter={16}>
                {validStringTclObj[TC].map((TCL, _) => (
                  <Col span={8} key={TCL}>
                    <Popover placement="left" content={input.tclData[TC].string[TCL]}>
                    <Checkbox value={TCL}>{TCL}</Checkbox>
                    </Popover>
                  </Col>
                ))}
              </Row>
            </Checkbox.Group>
          </>
        ))}
      </div>
    );
  }


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
      console.log(JSON.parse(res.data));
      setInputInfo(JSON.parse(res.data));
      // inputInfo = JSON.parse(res.data)
    }
    catch{
      message.error(`Fail to upload the TAC report`);
    }
    finally {
      hideMessage();
      message.success(`Success to parse ste file`);
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



  // Topk form
  const formItemLayout = {
    labelCol: {
      span: 12,
    },
    wrapperCol: {
      span: 8,
    },
  };

  const tips = 'The number of result B2B should between 0 and 100.';

  const validateTopk = (number) => {
    if (number > 0 || number < 101) {
      return {
        validateStatus: 'success',
        errorMsg: null,
      }
    }
    return {
      validateStatus: 'error',
      errorMsg: 'The number of result B2B should between 0 and 100.',
    }
  };

  const onChangeTopk = (value) => {
    setTopk({
      ...validateTopk(value),
      value,
    });
  };


  // Search button
  /**
   * Search most proper B2Bs with searching parameters. 
   * Call /Input API to the server with body parameter
   * - Parameter
   *  topk: How many B2Bs in the result list
   *  testCaseBoolean: List of checked Boolean variables 
   *  testCaseString: List of checked String variables
   * @param {*} event 
   */
  const onClickSearchCi = async(event) => {
    finalRequest.topk = topk.value;
    finalRequest.testCaseBoolean = ChangeObj2Pydantic(checkedBoolTclObj);
    finalRequest.testCaseString = ChangeObj2Pydantic(checkedStringTclObj);
    console.log(JSON.stringify(finalRequest));

    const hideMessage = message.loading(`Uploading TAC report to server`, 0);
    try{
      const finalURI = RESULTURL + '/' + inputInfo.key
      const res = await axios.post(finalURI, finalRequest, {
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      message.success(`Success to find!`);
      let B2BList = JSON.parse(res.data)
      navigate('/Result', { state: {
        B2BListParams: B2BList, 
        inputInfoParams: inputInfo,
        checkedBoolTclParams: checkedBoolTclObj,
        checkedStringTclParams: checkedStringTclObj,
      }});
    }
    catch(e) {
      message.error(`There is no matching B2B in CI phase.`);
    }
    finally {
      hideMessage();
    }
  };

  /**
   * Refresh the page if the user click the reset button.
   * @param {*} event 
   */
  const onClickReset = (event) => {
    navigate(0);
  };

  return (
    <>
      <Layout className="layout">
        <Header
          style={{ backgroundColor: "#2185D0" }}
        >
          <div className="logo" onClick={onClickLogo}/>
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
            {!inputInfo && (
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
                    <p className="logoMain"  align="center">
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
            )}
            {inputInfo && (
              <Space direction="vertical"
                size="large"
                style={{
                  display: 'flex',
                  width: '1200px',
                }}>
                <Card
                  style={{
                    width: '100%',
                    height: 250,
                    maxHeight: 250,
                    padding: '1% 2%',
                    overflow: "auto"
                  }}
                  bodyStyle={{ height: '100%', }}
                >
                  <Space direction="vertical" size="middle" style={{ display: 'flex' }}>
                    <Descriptions title="Input test suite information" bordered>
                      {showInfo()}
                    </Descriptions>
                  </Space>
                </Card>
                <Collapse defaultActiveKey={['1']}>
                  <Panel
                    header="Select most important Tcl variables"
                    key="1"
                  >
                    <Space
                      direction="vertical"
                      size="middle"
                      style={{
                        display: 'flex',
                      }}
                    >
                      {showCheckList()}
                    </Space>
                  </Panel>
                </Collapse>
                <Space
                  size={450}
                  style={{
                    width: '100%',
                    display: 'flex',
                    justifyContent: 'left',
                  }}
                  align = "baseline">
                  <Form
                    style={{
                      float: 'left'
                    }}
                  >
                    <Form.Item
                      {...formItemLayout}
                      label="The number of result B2Bs"
                      validateStatus={topk.validateStatus}
                      help={topk.errorMsg || tips}
                    >
                      <InputNumber min={0} max={100} value={topk.value} onChange={onChangeTopk} />
                    </Form.Item>
                  </Form>
                  <Space
                    size={30}
                    style={{
                      width: '100%',
                      display: 'flex',
                      justifyContent: 'center',
                    }}>
                    <Button
                      type="primary"
                      onClick={onClickSearchCi}
                    >
                      Search CI test suites
                    </Button>
                    <Button
                      onClick={onClickReset}
                    >
                      Reset
                    </Button>
                  </Space>
                </Space>
              </Space>
            )}
          </Content>
        </Layout>
        <Footer style={{ textAlign: 'center' }}>©2023 Spirent Communications, Inc. All rights reserved.</Footer>
      </Layout>
    </>
  );
}

export default MainPage;